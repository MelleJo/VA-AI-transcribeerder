import os
import streamlit as st
from utils.audio_processing import transcribe_audio, process_audio_input
from utils.file_processing import process_uploaded_file
from services.summarization_service import summarize_text
from ui.components import setup_page_style, display_transcript, display_summary
from ui.pages import render_feedback_form, render_conversation_history
from services.openai_service import initialize_openai_client
from utils.text_processing import update_gesprekslog, copy_to_clipboard

# Configuration
PROMPTS_DIR = os.path.abspath("prompts")
QUESTIONS_DIR = os.path.abspath("questions")

DEPARTMENTS = [
    "Bedrijven", "Financieel Advies", "Schadeafdeling", "Algemeen", "Arbo", "Algemene samenvatting",
    "Ondersteuning Bedrijfsarts", "Onderhoudsadviesgesprek in tabelvorm", "Notulen van een vergadering",
    "Verslag van een telefoongesprek", "Deelnemersgesprekken collectief pensioen", "test-prompt (alleen voor Melle!)"
]

INPUT_METHODS = ["Voer tekst in of plak tekst", "Upload tekst", "Upload audio", "Neem audio op"]

def load_config():
    return {
        "PROMPTS_DIR": PROMPTS_DIR,
        "QUESTIONS_DIR": QUESTIONS_DIR,
        "DEPARTMENTS": DEPARTMENTS,
        "INPUT_METHODS": INPUT_METHODS,
    }

# Initialize OpenAI client
initialize_openai_client(st.secrets["OPENAI_API_KEY"])

def main():
    config = load_config()
    setup_page_style()
    
    st.title("Gesprekssamenvatter - 0.2.1")

    col1, col2 = st.columns([1, 3])

    with col1:
        department = st.selectbox("Kies je afdeling", config["DEPARTMENTS"], key='department_select')
        input_method = st.radio("Wat wil je laten samenvatten?", config["INPUT_METHODS"], key='input_method_radio')

    with col2:
        if input_method == "Upload tekst":
            uploaded_file = st.file_uploader("Choose a file", type=['txt', 'docx', 'pdf'])
            if uploaded_file:
                st.session_state['transcript'] = process_uploaded_file(uploaded_file)
                st.session_state['summary'] = summarize_text(st.session_state['transcript'], department)
                update_gesprekslog(st.session_state['transcript'], st.session_state['summary'])

        elif input_method == "Voer tekst in of plak tekst":
            st.session_state['input_text'] = st.text_area("Voeg tekst hier in:", 
                                                          value=st.session_state.get('input_text', ''), 
                                                          height=300,
                                                          key='input_text_area')
            if st.button("Samenvatten", key='summarize_button'):
                if st.session_state['input_text']:
                    st.session_state['transcript'] = st.session_state['input_text']
                    st.session_state['summary'] = summarize_text(st.session_state['transcript'], department)
                    update_gesprekslog(st.session_state['transcript'], st.session_state['summary'])
                else:
                    st.warning("Voer alstublieft wat tekst in om te samenvatten.")

        elif input_method in ["Upload audio", "Neem audio op"]:
            process_audio_input(input_method)

        display_transcript(st.session_state.get('transcript', ''))
        display_summary(st.session_state.get('summary', ''))

        if st.session_state.get('summary'):
            if st.button("Kopieer naar klembord", key='copy_clipboard_button'):
                copy_to_clipboard(st.session_state['transcript'], st.session_state['summary'])
            render_feedback_form()

    render_conversation_history()

if __name__ == "__main__":
    main()