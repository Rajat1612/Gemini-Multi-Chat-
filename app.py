import streamlit as st
import google.generativeai as genai
from PyPDF2 import PdfReader
import sqlite3
import json
from datetime import datetime

# --- PAGE CONFIG ---
st.set_page_config(page_title="Gemini Multi-turn Chat", layout="centered")

# --- GEMINI API CONFIG ---
genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])

# --- DATABASE SETUP ---
def init_db():
    conn = sqlite3.connect("chat_history.db")
    c = conn.cursor()
    c.execute("""
    CREATE TABLE IF NOT EXISTS chat (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        timestamp TEXT,
        messages TEXT,
        context TEXT
    )
    """)
    conn.commit()
    return conn

conn = init_db()

# --- SESSION STATE ---
if "messages" not in st.session_state:
    st.session_state.messages = []
if "context" not in st.session_state:
    st.session_state.context = ""
if "chat_name" not in st.session_state:
    st.session_state.chat_name = ""
if "ask_load_history" not in st.session_state:
    st.session_state.ask_load_history = True

# --- FUNCTIONS ---
def auto_generate_name(messages):
    for msg in messages:
        if msg["role"] == "user":
            return msg["content"][:30] + ("..." if len(msg["content"]) > 30 else "")
    return "Untitled " + datetime.now().strftime("%Y-%m-%d %H:%M")

def save_chat():
    c = conn.cursor()
    name = st.session_state.chat_name or auto_generate_name(st.session_state.messages)
    c.execute("INSERT INTO chat (name, timestamp, messages, context) VALUES (?, ?, ?, ?)",
              (name,
               datetime.now().isoformat(),
               json.dumps(st.session_state.messages),
               st.session_state.context))
    conn.commit()

def get_all_chats(search_term=None):
    c = conn.cursor()
    c.execute("SELECT id, name, timestamp FROM chat ORDER BY id DESC")
    rows = c.fetchall()
    formatted = []
    for row in rows:
        chat_id, name, timestamp = row
        label = f"{name or 'Untitled'} – {timestamp}"
        if search_term and search_term.lower() not in label.lower():
            continue
        formatted.append((chat_id, label))
    return formatted

def load_chat_by_id(chat_id):
    c = conn.cursor()
    c.execute("SELECT name, messages, context FROM chat WHERE id = ?", (chat_id,))
    row = c.fetchone()
    if row:
        st.session_state.chat_name = row[0]
        st.session_state.messages = json.loads(row[1])
        st.session_state.context = row[2]
        st.success(f"Loaded chat: {row[0]}")

def rename_chat(chat_id, new_name):
    c = conn.cursor()
    c.execute("UPDATE chat SET name = ? WHERE id = ?", (new_name, chat_id))
    conn.commit()
    st.success(f"Renamed chat to: {new_name}")

def delete_chat(chat_id):
    c = conn.cursor()
    c.execute("DELETE FROM chat WHERE id = ?", (chat_id,))
    conn.commit()
    st.success(f"Deleted chat with ID: {chat_id}")

def delete_all_chats():
    c = conn.cursor()
    c.execute("DELETE FROM chat")
    conn.commit()
    st.success("All chat sessions deleted!")

def clear_chat():
    st.session_state.messages = []
    st.session_state.context = ""
    st.session_state.chat_name = ""
    st.success("Chat history cleared!")

# --- ASK TO LOAD HISTORY ---
if st.session_state.ask_load_history:
    st.info("Would you like to load one of your previous chat sessions?")
    search_term = st.text_input("Search your sessions by keyword (optional):")
    sessions = get_all_chats(search_term)
    if sessions:
        labels = [label for _, label in sessions]
        selected = st.selectbox("Select a chat session:", labels)
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Load selected session"):
                chat_id = next(cid for cid, label in sessions if label == selected)
                load_chat_by_id(chat_id)
                st.session_state.ask_load_history = False
                st.rerun()
        with col2:
            if st.button("Start fresh"):
                st.session_state.ask_load_history = False
                st.rerun()
    else:
        st.warning("No previous sessions found for your search.")
        if st.button("Start fresh anyway"):
            st.session_state.ask_load_history = False
            st.rerun()
    st.stop()

# --- SIDEBAR ---
st.sidebar.title("Controls")
if st.sidebar.button("Clear chat"):
    clear_chat()

st.sidebar.subheader("Manage saved sessions")
search_sidebar = st.sidebar.text_input("Search sessions here:")
sessions_sidebar = get_all_chats(search_sidebar)
if sessions_sidebar:
    session_labels = [label for _, label in sessions_sidebar]
    selected_manage = st.sidebar.selectbox("Select session:", session_labels)
    if st.sidebar.button("Delete selected session"):
        chat_id = next(cid for cid, label in sessions_sidebar if label == selected_manage)
        delete_chat(chat_id)
    new_name = st.sidebar.text_input("Rename selected session to:")
    if st.sidebar.button("Rename session"):
        chat_id = next(cid for cid, label in sessions_sidebar if label == selected_manage)
        rename_chat(chat_id, new_name)

    if st.sidebar.button("Delete all sessions"):
        delete_all_chats()

# --- MAIN APP ---
st.title(st.session_state.chat_name or "Gemini Multi-turn Chat")
st.write("Attach context (PDF/TXT/MD) to enhance your chat.")

# --- FILE UPLOAD ---
uploaded_files = st.file_uploader(
    "Attach context (PDF/TXT/MD)",
    type=["pdf", "txt", "md"],
    accept_multiple_files=True
)

if uploaded_files:
    context_text = ""
    for uploaded_file in uploaded_files:
        if uploaded_file.type == "application/pdf":
            reader = PdfReader(uploaded_file)
            for page in reader.pages:
                context_text += page.extract_text() + "\n"
        else:
            context_text += uploaded_file.read().decode("utf-8") + "\n"
    st.session_state.context = context_text
    st.success(f"Context loaded from {len(uploaded_files)} file(s)")

# --- DISPLAY PREVIOUS MESSAGES ---
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# --- USER INPUT ---
if user_input := st.chat_input("Say something..."):
    st.session_state.messages.append({"role": "user", "content": user_input})
    if not st.session_state.chat_name:
        st.session_state.chat_name = auto_generate_name(st.session_state.messages)

    with st.chat_message("user"):
        st.markdown(user_input)

    with st.chat_message("assistant"):
        try:
            model = genai.GenerativeModel("gemini-1.5-flash")
            chat_history = "\n".join([f"{m['role']}: {m['content']}" for m in st.session_state.messages])
            full_prompt = f"Context:\n{st.session_state.context}\n\nConversation so far:\n{chat_history}\n\nAssistant:"
            response = model.generate_content(full_prompt)
            reply = response.text.strip()
        except Exception as e:
            reply = f"Error: {str(e)}"

        st.markdown(reply)

    st.session_state.messages.append({"role": "assistant", "content": reply})
    save_chat()
