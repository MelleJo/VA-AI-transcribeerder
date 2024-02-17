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
    # Map the department name to its corresponding folder name, ensuring lowercase to match your structure
    department_to_folder = {
        "Schadebehandelaar": "schadebehandelaar",
        "Particulieren": "particulieren",
        "Bedrijven": "bedrijven",
        "Financiële Planning": "financiele planning"
    }
    folder_name = department_to_folder.get(department, "").lower()  # Default to empty string if department not found
    if not folder_name:  # If the department does not match, log an error
        st.error(f"Onbekende afdeling '{department}'. Kan het overeenkomstige promptbestand niet vinden.")
        return None

    # Construct the file path based on the mapped folder name
    prompt_file_path = os.path.join('prompts', folder_name, 'prompt.txt')  # Assuming each folder contains a 'prompt.txt'
    try:
        with open(prompt_file_path, 'r', encoding='utf-8') as file:
            return file.read()
    except FileNotFoundError:
        st.error(f"Promptbestand voor '{department}' niet gevonden. Verwachte bestandspad: {prompt_file_path}")
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


# Initialize session state variables
if 'department' not in st.session_state:
    st.session_state['department'] = ''
if 'direct_text' not in st.session_state:
    st.session_state['direct_text'] = ''

# Streamlit App UI
def app_ui():
    st.title("VA Gesprekssamenvatter")

    # Afdeling selectie met prompt laden
    department = st.selectbox("Kies uw afdeling:", ["Schadebehandelaar", "Particulieren", "Bedrijven", "Financiële Planning"])
    st.session_state['department'] = department
    
    prompt_text = load_prompt(st.session_state['department'])
    if prompt_text is None:
        st.error("Kon het promptbestand voor '{}' niet vinden. Controleer de naam van de afdeling en het overeenkomende promptbestand.".format(department))
        return
    
    # Tekstinvoer verwerken
    user_input = st.text_area("Plak hier uw tekst:", height=250)

    # MP3-bestand uploaden
    uploaded_file = st.file_uploader("Of upload een MP3-bestand voor transcriptie:", type=["mp3"])
    
    # Knop om de samenvatting te genereren
    if st.button("Genereer Samenvatting"):
        direct_text = user_input  # Gebruik direct ingevoerde tekst als standaard
        
        if uploaded_file is not None:
            # Plaatsvervanger: Implementeer hier uw transcriptielogica
            # Aannemend dat `transcribe_audio` uw functie is om transcriptie te verwerken
            direct_text = transcribe_audio(uploaded_file, SPEECHMATICS_AUTH_TOKEN)
        
        if direct_text:
            # Aannemend dat `summarize_text` uw functie is om de samenvatting te verwerken
            # Deze zou de tekst (of getranscribeerde tekst), het geladen prompt en de OpenAI API-sleutel moeten nemen
            summary = summarize_text(direct_text, prompt_text, st.secrets["openai"]["api_key"])
            st.subheader("Samenvatting")
            st.write(summary)
        else:
            st.error("Voer alstublieft wat tekst in of upload een MP3-bestand.")


app_ui()
