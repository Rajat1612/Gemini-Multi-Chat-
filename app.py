import os
import streamlit as st
import google.generativeai as genai

# --- App Config ---
st.set_page_config(page_title="Gemini Multi-turn Chat", layout="centered")
st.title("Gemini Multi-turn Chat")

# --- Debug: Check API Key ---
api_key = os.getenv("GOOGLE_API_KEY")
if not api_key:
    st.error("❌ GOOGLE_API_KEY not found. Please set it in Streamlit → Settings → Secrets.")
    st.stop()

# --- Configure Gemini ---
genai.configure(api_key=api_key)
model = genai.GenerativeModel("gemini-1.5-flash")

# --- Initialize Chat Memory ---
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

# --- Display Chat History ---
for message in st.session_state.chat_history:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# --- Chat Input ---
if prompt := st.chat_input("Say something..."):
    # Add user message to history
    st.session_state.chat_history.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Generate response
    try:
        response = model.generate_content(prompt)
        bot_reply = response.text
    except Exception as e:
        bot_reply = f"⚠️ Error: {e}"

    # Add assistant message to history
    st.session_state.chat_history.append({"role": "assistant", "content": bot_reply})
    with st.chat_message("assistant"):
        st.markdown(bot_reply)

