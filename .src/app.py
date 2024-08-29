import streamlit as st
import os
import sys
import json
from openai_service import perform_gpt4_operation
from utils.audio_processing import process_audio_input
from services.summarization_service import run_summarization
from utils.file_processing import process_uploaded_file
from ui.pages import render_wizard, render_feedback_form, render_conversation_history, setup_page_style
from ui.components import initialize_session_state
from utils.text_processing import update_gesprekslog, load_questions
from docx import Document
from io import BytesIO
import bleach
import base64
import time
import logging
from config import BASE_DIR

logger = logging.getLogger(__name__)

# Configuration
PROMPTS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), 'prompts'))
QUESTIONS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'questions'))

# Set the page configuration
st.set_page_config(page_title="Gesprekssamenvatter", page_icon="🎙️", layout="wide")

# Business logic dictionaries
BUSINESS_SIDES = {
    "VA": {
        "Veldhuis Advies": [
            "AOV", "Collectief pensioen", "Deelnemersgesprekken collectief pensioen",
            "Financieelplanningstraject", "Hypotheek rapport", "Hypotheek",
            "Ingesproken handleiding", "Ingesproken notitie", "Notulen brainstorm",
            "Notulen vergadering", "Onderhoudsadviesgesprek werkgever", "Pensioen",
            "Samenvatting_gesprek_bedrijfsarts", "Telefoongesprek"
        ],
        "Algemeen": ["Ingesproken handleiding", "Notulen brainstorm", "Notulen vergadering"]
    },
    "VAG": {
        "Schade": [
            "Expertise gesprek", "Ingesproken handleiding", "Ingesproken notitie",
            "Notulen brainstorm", "Notulen vergadering", "Schade beoordeling",
            "Schademelding", "Telefoongesprek"
        ],
        "Particulieren": [
            "Adviesgesprek", "Ingesproken handleiding", "Ingesproken notitie",
            "Mutatie", "Notulen brainstorm", "Notulen vergadering", "Telefoongesprek"
        ],
        "Bedrijven": [
            "Adviesgesprek tabelvorm", "Adviesgesprek", "Ingesproken handleiding",
            "Ingesproken notitie", "Klantrapport", "Klantvraag", "Notulen brainstorm",
            "Notulen vergadering", "Onderhoudsadviesgesprek tabel prompt", "Risico analyse",
            "Telefoongesprek"
        ],
        "Algemeen": ["Ingesproken handleiding", "Notulen brainstorm", "Notulen vergadering"]
    },
    "Arbo": {
        "Arbo": [
            "Gesprek bedrijfsarts", "Ingesproken handleiding", "Ingesproken notitie",
            "Notulen brainstorm", "Notulen vergadering", "Telefoongesprek"
        ],
        "Algemeen": ["Ingesproken handleiding", "Notulen brainstorm", "Notulen vergadering"]
    }
}

DEPARTMENTS = {
    "Schade": ["Schademelding", "Telefoongesprek", "Schade beoordeling", "Expertise gesprek", "Ingesproken notitie"],
    "Bedrijven": ["Adviesgesprek", "Adviesgesprek tabelvorm", "Risico analyse", "Klantvraag", "Telefoongesprek", "Ingesproken notitie", "Klantrapport"],
    "Particulieren": ["Mutatie", "Telefoongesprek", "Adviesgesprek", "Ingesproken notitie"],
    "Arbo": ["Telefoongesprek", "Ingesproken notitie", "Gesprek bedrijfsarts"],
    "Veldhuis Advies": ["Pensioen", "Collectief pensioen", "Hypotheek", "Hypotheek rapport", "Financieelplanningstraject", "Deelnemersgesprekken collectief pensioen", "AOV", "Telefoongesprek", "Ingesproken notitie"],
    "Algemeen": ["Notulen vergadering", "Notulen brainstorm", "Ingesproken handleiding"]
}

INPUT_METHODS = ["Voer tekst in of plak tekst", "Upload tekst", "Upload audio", "Neem audio op"]

def main():
    setup_page_style()
    initialize_session_state()

    st.session_state.BUSINESS_SIDES = BUSINESS_SIDES
    st.session_state.INPUT_METHODS = INPUT_METHODS

    render_wizard()

    st.markdown("---")
    st.markdown("### Extra opties")

    tab1, tab2 = st.tabs(["Geef feedback", "Bekijk gespreksgeschiedenis"])

    with tab1:
        render_feedback_form()

    with tab2:
        render_conversation_history()


if __name__ == "__main__":
    main()
