import streamlit as st
import os
import sys
import json
from .src.ui.pages import render_wizard, render_feedback_form, render_conversation_history
from .src.ui.components import setup_page_style, initialize_session_state

from io import BytesIO
import bleach
import base64
import time
import logging

logger = logging.getLogger(__name__)

# Configuration
PROMPTS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), 'prompts'))
QUESTIONS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'questions'))

BUSINESS_SIDES = ["Veldhuis Advies Groep", "Veldhuis Advies", "Arbo"]

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

    st.session_state.PROMPTS_DIR = PROMPTS_DIR
    st.session_state.QUESTIONS_DIR = QUESTIONS_DIR
    st.session_state.BUSINESS_SIDES = BUSINESS_SIDES
    st.session_state.DEPARTMENTS = DEPARTMENTS
    st.session_state.INPUT_METHODS = INPUT_METHODS

    render_wizard()
    render_feedback_form()
    render_conversation_history()

if __name__ == "__main__":
    main()