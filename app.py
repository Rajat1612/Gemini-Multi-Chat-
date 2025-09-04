import os
import streamlit as st
import google.generativeai as genai
from io import StringIO

# ==== App Config ====
st.set_page_config(page_title="Gemini Multi-turn Chat", layout="centered")
st.title("Gemini Multi-turn Chat")

# ==== API Key ====
api_key = os.getenv("GOOGLE_API_KEY")
if not api_key:
    st.error("❌ GOOGLE_API_KEY not found. Please set it in Streamlit → Settings → Secrets.")
    st.stop()

# ==== Configure Gemini ====
genai.configure(api_key=api_key)
model = genai.GenerativeModel("gemini-1.5-flash")

# ==== Initialize Session State ====
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "user_name" not in st.session_state:
    st.session_state.user_name = "Rajat"  # Default name

# ==== Display Chat History ====
for message in st.session_state.chat_history:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# ==== Chat Input ====
if prompt := st.chat_input("Say something..."):
    st.session_state.chat_history.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Modify prompt to include your name
    full_prompt = f"{st.session_state.user_name} says: {prompt}"

    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            response = model.generate_content(full_prompt)
            reply = response.text
            st.markdown(reply)
            st.session_state.chat_history.append({"role": "assistant", "content": reply})

# ==== Download Chat Feature ====
if st.session_state.chat_history:
    chat_text = "\n".join([f"{m['role'].capitalize()}: {m['content']}" for m in st.session_state.chat_history])
    st.download_button(
        label="Download chat",
        data=chat_text,
        file_name="chat_history.txt",
        mime="text/plain"
    )
