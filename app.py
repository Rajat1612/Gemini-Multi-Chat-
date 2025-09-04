import streamlit as st
import sqlite3
import json
from datetime import datetime

st.set_page_config(page_title="Gemini Multi-turn Chat", layout="wide")
st.title("Gemini Multi-turn Chat")

# --- Persistent SQLite Storage ---
conn = sqlite3.connect("chat_history.db", check_same_thread=False)
c = conn.cursor()

c.execute("""
CREATE TABLE IF NOT EXISTS chat_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT,
    chat_data TEXT,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
""")
conn.commit()

SESSION_ID = "global_session"

# --- Load previous chat history ---
c.execute("SELECT chat_data FROM chat_history WHERE session_id=?", (SESSION_ID,))
row = c.fetchone()
if row:
    st.session_state.chat_history = json.loads(row[0])
else:
    st.session_state.chat_history = []

# --- Sidebar Controls ---
with st.sidebar:
    st.subheader("Controls")
    persist = st.checkbox("Persist chat in SQLite (best-effort)", value=True)
    if st.button("Clear chat"):
        st.session_state.chat_history = []
        c.execute("DELETE FROM chat_history WHERE session_id=?", (SESSION_ID,))
        conn.commit()
        st.experimental_rerun()

# --- File Upload Section ---
st.subheader("Attach context (PDF/TXT/MD)")
uploaded_files = st.file_uploader("Drag and drop files here", type=["pdf", "txt", "md"], accept_multiple_files=True)
if uploaded_files:
    st.success(f"Uploaded: {', '.join([file.name for file in uploaded_files])}")

# --- Display Chat History ---
for msg in st.session_state.chat_history:
    if msg["role"] == "user":
        st.chat_message("user").markdown(msg["content"])
    else:
        st.chat_message("assistant").markdown(msg["content"])

# --- Chat Input ---
user_input = st.chat_input("Say something...")
if user_input:
    st.session_state.chat_history.append({"role": "user", "content": user_input})

    # Mock Gemini response (replace with your Gemini API call)
    assistant_reply = f"Echo: {user_input}"
    st.session_state.chat_history.append({"role": "assistant", "content": assistant_reply})

    # Save to SQLite
    if persist:
        c.execute(
            "INSERT OR REPLACE INTO chat_history (session_id, chat_data, updated_at) VALUES (?, ?, ?)",
            (SESSION_ID, json.dumps(st.session_state.chat_history), datetime.utcnow())
        )
        conn.commit()

    st.experimental_rerun()
