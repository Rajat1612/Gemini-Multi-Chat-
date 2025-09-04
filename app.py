import os
import uuid
import sqlite3
from io import BytesIO

import streamlit as st
import google.generativeai as genai

# Optional PDF parsing (local, no external upload to Google)
try:
    from pypdf import PdfReader
    PDF_OK = True
except Exception:
    PDF_OK = False

# ---------- App & Theme ----------
st.set_page_config(page_title="Gemini Multi-turn Chat", layout="centered")
st.markdown(
    """
    <style>
    .chat-bubble {padding: .9rem 1rem; border-radius: 1rem; margin: .35rem 0; max-width: 800px;}
    .user      {background: #eef2ff; border: 1px solid #dbeafe;}
    .assistant {background: #f7fee7; border: 1px solid #ecfccb;}
    .role      {font-size:.85rem; opacity:.7; margin-bottom:.35rem;}
    .ctx-chip  {display:inline-block; padding:.25rem .5rem; border-radius:.75rem; border:1px solid #e5e7eb; background:#fafafa; margin-right:.35rem; font-size:.8rem;}
    .small     {font-size:.85rem;}
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("Gemini Multi-turn Chat")

# ---------- API Key ----------
API_KEY = os.getenv("GOOGLE_API_KEY")
if not API_KEY:
    st.error("❌ GOOGLE_API_KEY missing. In Streamlit → **Manage app → Settings → Secrets**, add:\n\n`GOOGLE_API_KEY = your_key`")
    st.stop()

genai.configure(api_key=API_KEY)
MODEL_NAME = "gemini-1.5-flash"  # fast & inexpensive

# ---------- Session & (optional) persistence ----------
if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []  # [{role:"user|assistant", content:"..."}]

if "context_blob" not in st.session_state:
    st.session_state.context_blob = ""  # concatenated text from uploads

# Simple SQLite persistence (keeps history per session_id). Note: Streamlit Cloud
# storage can be ephemeral; this is best-effort persistence, not guaranteed.
DB_PATH = "chat_memory.sqlite"

def init_db():
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                session_id TEXT,
                ts INTEGER,
                role TEXT,
                content TEXT
            )
        """)
        conn.commit()
        return conn
    except Exception:
        return None

def save_msg(conn, role, content):
    if not conn: return
    conn.execute(
        "INSERT INTO messages (session_id, ts, role, content) VALUES (?, strftime('%s','now'), ?, ?)",
        (st.session_state.session_id, role, content),
    )
    conn.commit()

def load_history(conn):
    if not conn: return []
    cur = conn.execute(
        "SELECT role, content FROM messages WHERE session_id=? ORDER BY ts ASC",
        (st.session_state.session_id,),
    )
    return [{"role": r, "content": c} for (r, c) in cur.fetchall()]

# Sidebar controls
with st.sidebar:
    st.subheader("Controls")
    use_persistence = st.checkbox("Persist chat in SQLite (best-effort)", value=True)
    if st.button("🗑️ Clear chat"):
        st.session_state.chat_history = []
        st.session_state.context_blob = ""
        if use_persistence:
            conn_tmp = init_db()
            if conn_tmp:
                conn_tmp.execute("DELETE FROM messages WHERE session_id=?", (st.session_state.session_id,))
                conn_tmp.commit()
                conn_tmp.close()
        st.experimental_rerun()

    st.caption("Tip: Upload files to ground the answers in your content.")

# Load persisted history (once per run)
if use_persistence:
    _conn = init_db()
    if _conn and not st.session_state.chat_history:
        st.session_state.chat_history = load_history(_conn)
else:
    _conn = None

# ---------- File upload for context ----------
uploaded = st.file_uploader(
    "Attach context (PDF/TXT/MD). The model will use this along with chat history.",
    type=["pdf", "txt", "md"],
    accept_multiple_files=True,
)

def extract_text(file):
    name = file.name.lower()
    if name.endswith((".txt", ".md")):
        return file.read().decode("utf-8", errors="ignore")
    if name.endswith(".pdf") and PDF_OK:
        text_parts = []
        reader = PdfReader(BytesIO(file.read()))
        for page in reader.pages:
            text_parts.append(page.extract_text() or "")
        return "\n".join(text_parts)
    if name.endswith(".pdf") and not PDF_OK:
        st.warning("PDF support requires package `pypdf`. Add it to requirements.txt.")
        return ""
    return ""

if uploaded:
    merged = []
    for f in uploaded:
        try:
            merged.append(extract_text(f))
        except Exception as e:
            st.warning(f"Failed to read {f.name}: {e}")
    st.session_state.context_blob = "\n\n".join([t for t in merged if t]).strip()

# Show context chips
if st.session_state.context_blob:
    st.markdown('<div class="ctx-chip">📎 Context attached</div><span class="small">Answers will use your uploaded text.</span>', unsafe_allow_html=True)

# ---------- Render history ----------
for m in st.session_state.chat_history:
    role_cls = "assistant" if m["role"] == "assistant" else "user"
    who = "Assistant" if m["role"] == "assistant" else "You"
    st.markdown(f'<div class="chat-bubble {role_cls}"><div class="role">{who}</div>{m["content"]}</div>', unsafe_allow_html=True)

# ---------- Chat input ----------
prompt = st.chat_input("Say something...")
if prompt:
    # Add user message
    st.session_state.chat_history.append({"role": "user", "content": prompt})
    if _conn and use_persistence:
        save_msg(_conn, "user", prompt)

    # Compose model input with memory + optional context
    history_text = "\n".join(
        [("User: " if h["role"] == "user" else "Assistant: ") + h["content"] for h in st.session_state.chat_history]
    )
    context_section = f"\n\n[Context]\n{st.session_state.context_blob[:8000]}" if st.session_state.context_blob else ""
    system_preamble = (
        "You are a helpful assistant. Use the conversation history and any provided context to answer. "
        "If the answer is in the context, cite it briefly; if not, answer normally."
    )

    full_input = f"{system_preamble}\n\n[Conversation so far]\n{history_text}{context_section}\n\nAssistant:"
    model = genai.GenerativeModel(MODEL_NAME)

    # Stream the reply
    placeholder = st.empty()
    bot_reply = ""
    try:
        response = model.generate_content(full_input, stream=True)
        for chunk in response:
            if hasattr(chunk, "text") and chunk.text:
                bot_reply += chunk.text
                placeholder.markdown(
                    f'<div class="chat-bubble assistant"><div class="role">Assistant</div>{bot_reply}</div>',
                    unsafe_allow_html=True,
                )
        response.resolve()
    except Exception as e:
        bot_reply = f"⚠️ Error: {e}"
        placeholder.markdown(
            f'<div class="chat-bubble assistant"><div class="role">Assistant</div>{bot_reply}</div>',
            unsafe_allow_html=True,
        )

    # Persist assistant message & update state
    st.session_state.chat_history.append({"role": "assistant", "content": bot_reply})
    if _conn and use_persistence:
        save_msg(_conn, "assistant", bot_reply)
