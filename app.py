import streamlit as st

st.set_page_config(page_title="Gemini Multi-turn Chat", layout="centered")
st.write("🔄 App is reloading... If you see this, deployment is working.")

st.title("Gemini Multi-turn Chat")
st.write("Your Streamlit app is running successfully!")

# Simple text input
user_input = st.text_input("Say something:")
if st.button("Submit"):
    st.write(f"You said: {user_input}")
