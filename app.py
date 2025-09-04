import streamlit as st
import sqlite3
import json
import os

# ---------------------------
# Page Config
# ---------------------------
st.set_page_config(page_title="Gemini Multi-turn Chat", layout="centered")
st.title("Gemini Multi-turn Chat")
st.write("Attach context (PDF/TXT/MD) and chat seamlessly across browsers!")

# ---------------------------
# Database Setup
# ---------------------------
DB_FILE = "chat_history.db"
conn = sqlite3.connect(DB_FILE)
c = conn.cursor()

c.execute('''
CREATE TABLE IF NOT EXISTS chat_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT,
    chat_data TEXT
)
''')
conn.commit()

# Use a global session ID to sync across browsers
SESSION_ID = "global_chat_session"

# ---------------------------
# Load Previous Chat
# ---------------------------
c.execute("SELECT chat_data FROM chat_history WHERE session_id=?", (SESSION_ID,))
row = c.fetchone()

if 'chat' not in st.session_state:
    if row:
        st.session_state.chat = json.loads(row[0])
    else:
        st.session_state.chat = []

# ---------------------------
# File Upload Section
# ---------------------------
uploaded_file = st.file_uploader("Drag and drop files here", type=["pdf", "txt", "md", "docx"])
if uploaded_file is not None:
    os.makedirs("uploads", exist_ok=True)
    file_path = os.path.join("uploads", uploaded_file.name)
    with open(file_path, "wb") as f:
        f.write(uploaded_file.getbuffer())
    st.success(f"Uploaded: {uploaded_file.name}")

# ---------------------------
# Chat Display
# ---------------------------
for msg in st.session_state.chat:
    if msg["role"] == "user":
        st.chat_message("user").write(msg["content"])
    else:
        st.chat_message("assistant").write(msg["content"])

# ---------------------------
# New Message Input
# ---------------------------
user_input = st.chat_input("Say something...")
if user_input:
    # Save user message
    st.session_state.chat.append({"role": "user", "content": user_input})

    # Simulate assistant response (replace with Gemini API call)
    assistant_response = f"You said: {user_input}"
    st.session_state.chat.append({"role": "assistant", "content": assistant_response})

    # Save chat to DB
    c.execute("INSERT OR REPLACE INTO chat_history (session_id, chat_data) VALUES (?, ?)",
              (SESSION_ID, json.dumps(st.session_state.chat)))
    conn.commit()

    st.experimental_rerun()
