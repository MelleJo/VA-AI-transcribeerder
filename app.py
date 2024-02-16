import streamlit as st
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
import os
import re
import time

# Setup for Speechmatics - Ensure you have these details correctly configured
SPEECHMATICS_URL = "https://api.speechmatics.com/v2"
SPEECHMATICS_AUTH_TOKEN = "your_speechmatics_auth_token_here"

# Function to load the appropriate prompt based on the department selected
def load_prompt(department):
    # Make sure the file names match the department names exactly
    prompt_file_path = f"./prompts/{department.replace(' ', '_').lower()}.txt"
    try:
        with open(prompt_file_path, 'r', encoding='utf-8') as file:
            return file.read()
    except FileNotFoundError:
        st.error(f"Prompt file for '{department}' not found.")
        return None

# Function to preprocess and split text for summarization
def preprocess_and_split_text(text, max_length=2000):
    # Preprocess to remove extra spaces
    text = re.sub(r'\s+', ' ', text.strip())
    # Split text into segments
    return [text[i:i+max_length] for i in range(0, len(text), max_length)]

# Function to generate a response from OpenAI based on the loaded prompt and text
def generate_response(text, prompt, openai_api_key):
    if prompt is None:
        prompt = "Please summarize this text:"
    full_prompt = f"{prompt}\n\n{text}"
    model = ChatOpenAI(api_key=openai_api_key, model_name="gpt-4", temperature=0.7)
    prompt_template = ChatPromptTemplate.from_template(full_prompt)
    chain = prompt_template | model | StrOutputParser()
    return chain.invoke({"text": text})

# Streamlit App UI
def app_ui():
    st.title("VA gesprekssamenvatter")

    # Department selection
    department = st.selectbox("Kies uw afdeling:", ["Schadebehandelaar", "Particulieren", "Bedrijven", "Financiële Planning"])
    prompt_text = load_prompt(department)

    # Text input
    user_input = st.text_area("Plak de tekst hier of upload een MP3-bestand voor transcriptie:", height=250)
    uploaded_file = st.file_uploader("Upload MP3", type=["mp3"])

    if st.button("Genereer samenvatting"):
        if uploaded_file:
            # Placeholder for MP3 transcription logic
            transcript = "Transcribed text from the MP3 file goes here."
            st.session_state['direct_text'] = transcript
        else:
            st.session_state['direct_text'] = user_input

        # Generate and display summary
        if st.session_state['direct_text']:
            segments = preprocess_and_split_text(st.session_state['direct_text'])
            summaries = [generate_response(segment, prompt_text, st.secrets["openai"]["api_key"]) for segment in segments]
            st.subheader("Samenvatting")
            st.write(" ".join(summaries))
        else:
            st.error("Geen geldige tekst of audio geüpload.")

app_ui()
