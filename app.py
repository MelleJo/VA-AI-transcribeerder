import streamlit as st
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
import os
import re
import time

def load_prompt(department):
    if department == "Financiële Planning":
        file_name = "financiele planning"
    else:
        file_name = department.replace(' ', '_').lower()
    prompt_file_path = f'prompts/{file_name}'
    try:
        with open(prompt_file_path, 'r', encoding='utf-8') as file:
            return file.read()
    except FileNotFoundError:
        st.error(f"Promptbestand voor '{department}' niet gevonden. Verwacht bestandspad: {prompt_file_path}")
        return ""

def preprocess_and_split_text(text, max_length=3000):
    text = re.sub(r'\s+', ' ', text.strip())
    return [text[i:i+max_length] for i in range(0, len(text), max_length)]

def generate_response(text, prompt, openai_api_key):
    full_prompt = f"{prompt}\n\n{text}"
    model = ChatOpenAI(api_key=openai_api_key, model_name="gpt-4", temperature=0.7)
    prompt_template = ChatPromptTemplate.from_template(full_prompt)
    chain = prompt_template | model | StrOutputParser()
    return chain.invoke({"text": text})

def app_ui():
    st.title("VA Gesprekssamenvatter")
    department = st.selectbox("Kies uw afdeling:", ["Schadebehandelaar", "Particulieren", "Bedrijven", "Financiële Planning"])
    speaker1 = st.text_input("Naam van Spreker 1 (optioneel):")
    speaker2 = st.text_input("Naam van Spreker 2 (optioneel):")
    subject = st.text_input("Onderwerp van het gesprek (optioneel):")
    user_input = st.text_area("Plak hier uw tekst:", height=250)
    uploaded_file = st.file_uploader("Of upload een MP3-bestand voor transcriptie:", type=["mp3"])
    
    if st.button("Genereer Samenvatting"):
        direct_text = user_input
        if direct_text:
            segments = preprocess_and_split_text(direct_text)
            summaries = [generate_response(segment, load_prompt(department), st.secrets["openai"]["api_key"]) for segment in segments]
            final_summary = " ".join(summaries)
            st.subheader("Samenvatting")
            st.write(final_summary)
        else:
            st.error("Voer alstublieft wat tekst in of upload een MP3-bestand.")

app_ui()
