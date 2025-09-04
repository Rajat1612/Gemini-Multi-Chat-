import os
import streamlit as st
import google.generativeai as genai
from PyPDF2 import PdfReader

# --- App Config ---
st.set_page_config(page_title="Gemini Multi-turn Chat", layout="centered")
st.title("Gemini Multi-turn Chat")

# --- API Key Configuration ---
api_key = os.getenv("GOOGLE_API_KEY")
if not api_key:
    st.error("❌ GOOGLE_API_KEY not found. Please set it in Streamlit → Settings → Secrets.")
    st.stop()
genai.configure(api_key=api_key)

# --- Initialize Gemini Model ---
model = genai.GenerativeModel("gemini-1.5-flash")

# --- Initialize Session State ---
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "user_name" not in st.session_state:
    st.session_state.user_name = None
if "uploaded_content" not in st.session_state:
    st.session_state.uploaded_content = ""

# --- Sidebar Controls ---
st.sidebar.header("Controls")
persist_chat = st.sidebar.checkbox("Persist chat in SQLite (best-effort)", value=True)
if st.sidebar.button("Clear chat"):
    st.session_state.chat_history = []
    st.session_state.user_name = None
    st.session_state.uploaded_content = ""
    st.success("Chat cleared!")

# --- File Upload ---
st.subheader("Attach context (PDF/TXT/MD)")
uploaded_file = st.file_uploader("Drag and drop files here", type=["pdf", "txt", "md"])
if uploaded_file:
    file_text = ""
    if uploaded_file.type == "application/pdf":
        reader = PdfReader(uploaded_file)
        for page in reader.pages:
            file_text += page.extract_text() + "\n"
    else:
        file_text = uploaded_file.read().decode("utf-8")

    st.session_state.uploaded_content = file_text
    st.success(f"File '{uploaded_file.name}' uploaded and added to context.")

# --- Display Chat History ---
for message in st.session_state.chat_history:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# --- Chat Input ---
if prompt := st.chat_input("Say something..."):
    # Capture user name if not yet known
    if st.session_state.user_name is None and ("my name is" in prompt.lower() or "i am" in prompt.lower()):
        st.session_state.user_name = prompt.split()[-1].strip(" .,")

    st.chat_message("user").markdown(prompt)
    st.session_state.chat_history.append({"role": "user", "content": prompt})

    # Build the full context for Gemini
    full_context = ""
    if st.session_state.user_name:
        full_context += f"User's name is {st.session_state.user_name}. "
    if st.session_state.uploaded_content:
        full_context += f"Context from uploaded document: {st.session_state.uploaded_content}\n"
    for msg in st.session_state.chat_history:
        full_context += f"{msg['role']}: {msg['content']}\n"

    response = model.generate_content(full_context)
    reply = response.text if hasattr(response, "text") else "I'm here to help!"

    with st.chat_message("assistant"):
        st.markdown(reply)

    st.session_state.chat_history.append({"role": "assistant", "content": reply})
