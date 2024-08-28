import streamlit as st
from streamlit_option_menu import option_menu
from streamlit_card import card
import os
import sys
import json
from openai_service import perform_gpt4_operation
from utils.audio_processing import process_audio_input
from utils.file_processing import process_uploaded_file
from services.summarization_service import run_summarization
from ui.components import display_transcript, display_summary
from ui.pages import render_feedback_form, render_conversation_history
from utils.text_processing import update_gesprekslog, load_questions
from docx import Document
from docx.shared import Pt
from docx.enum.style import WD_STYLE_TYPE
from io import BytesIO
import bleach
import base64
import time
import logging


logger = logging.getLogger(__name__)

# Configuration
PROMPTS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'prompts'))
QUESTIONS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'questions'))

BUSINESS_SIDES = ["Veldhuis Advies Groep", "Veldhuis Advies", "Arbo"]

DEPARTMENTS = {
    "Veldhuis Advies Groep": ["Algemeen", "Schade", "Bedrijven", "Particulieren", "Support"],
    "Veldhuis Advies": ["Algemeen", "Financiële Planning", "Pensioenen", "Hypotheek"],
    "Arbo": ["Algemeen", "Arbo"]
}

PROMPTS = {
    "Algemeen": ["Notulen van een vergadering", "Verslag van een telefoongesprek"],
    "Schade": ["Schademelding", "Schade-expertise"],
    "Bedrijven": ["Onderhoudsadviesgesprek", "Risico-inventarisatie"],
    "Particulieren": ["Adviesgesprek", "Polischeck"],
    "Support": ["Klantenservice", "Technische ondersteuning"],
    "Financiële Planning": ["Financieel plan", "Vermogensanalyse"],
    "Pensioenen": ["Pensioenadvies", "Collectief pensioen"],
    "Hypotheek": ["Hypotheekadvies", "Hypotheekberekening"],
    "Arbo": ["Verzuimbegeleiding", "Werkplekonderzoek"]
}

INPUT_METHODS = ["Voer tekst in of plak tekst", "Upload tekst", "Upload audio", "Neem audio op"]

def setup_page_style():
    st.set_page_config(page_title="Gesprekssamenvatter", page_icon="🎙️", layout="wide")
    st.markdown("""
    <style>
    .main {
        background-color: #f0f8ff;
        color: #333;
        font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
    }
    .stButton>button {
        background-color: #4CAF50;
        color: white;
        border: none;
        padding: 12px 28px;
        text-align: center;
        text-decoration: none;
        display: inline-block;
        font-size: 16px;
        margin: 4px 2px;
        cursor: pointer;
        border-radius: 30px;
        transition: all 0.3s ease 0s;
        box-shadow: 0 8px 15px rgba(0, 0, 0, 0.1);
    }
    .stButton>button:hover {
        background-color: #45a049;
        box-shadow: 0 15px 20px rgba(46, 229, 157, 0.4);
        transform: translateY(-7px);
    }
    .summary-box {
        border: none;
        border-radius: 15px;
        padding: 25px;
        margin: 20px 0;
        background-color: #ffffff;
        box-shadow: 0 10px 30px rgba(0, 0, 0, 0.1);
        transition: all 0.3s ease;
    }
    .summary-box:hover {
        box-shadow: 0 15px 40px rgba(0, 0, 0, 0.15);
        transform: translateY(-5px);
    }
    .summary-box h3 {
        color: #2c3e50;
        border-bottom: 2px solid #3498db;
        padding-bottom: 10px;
        margin-bottom: 20px;
        text-align: center;
        font-weight: 600;
    }
    .content {
        white-space: pre-wrap;
        word-wrap: break-word;
        font-size: 16px;
        line-height: 1.8;
        color: #34495e;
    }
    .transcript-box {
        border: none;
        border-radius: 10px;
        padding: 15px;
        margin-bottom: 20px;
        background-color: #f9f9f9;
        box-shadow: 0 5px 15px rgba(0, 0, 0, 0.05);
    }
    .copy-button {
        text-align: center;
        margin-top: 20px;
    }
    .stProgress > div > div > div > div {
        background-color: #3498db;
    }
    .stSelectbox {
        color: #2c3e50;
    }
    .stSelectbox > div > div {
        background-color: #ffffff;
        border-radius: 5px;
    }
    .stRadio > div {
        background-color: #ffffff;
        border-radius: 5px;
        padding: 10px;
        box-shadow: 0 2px 5px rgba(0, 0, 0, 0.05);
    }
    </style>
    """, unsafe_allow_html=True)

def initialize_session_state():
    defaults = {
        'summary': "",
        'summary_versions': [],
        'current_version_index': -1,
        'business_side': "",
        'department': "",
        'prompt': "",
        'input_method': "",
        'input_text': "",
        'transcript': "",
        'gesprekslog': [],
        'product_info': "",
        'selected_products': [],
        'transcription_done': False,
        'summarization_done': False,
        'processing_complete': False,
        'current_step': 0
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

def render_wizard():
    st.title("Gesprekssamenvatter Wizard")

    # Navigation
    steps = ["Bedrijfskant", "Afdeling", "Prompt", "Invoermethode", "Samenvatting"]
    selected_step = option_menu(
        menu_title=None,
        options=steps,
        icons=["building", "people-fill", "chat-left-text", "input-cursor-text", "file-text"],
        menu_icon="cast",
        default_index=st.session_state.current_step,
        orientation="horizontal",
    )

    # Update current step based on selection
    st.session_state.current_step = steps.index(selected_step)

    # Render the appropriate step
    if st.session_state.current_step == 0:
        render_business_side_selection()
    elif st.session_state.current_step == 1:
        render_department_selection()
    elif st.session_state.current_step == 2:
        render_prompt_selection()
    elif st.session_state.current_step == 3:
        render_input_method_selection()
    elif st.session_state.current_step == 4:
        render_summary()

    # Navigation buttons
    col1, col2, col3 = st.columns([1, 1, 1])
    with col1:
        if st.session_state.current_step > 0:
            if st.button("Vorige"):
                st.session_state.current_step -= 1
                st.experimental_rerun()
    with col3:
        if st.session_state.current_step < len(steps) - 1:
            if st.button("Volgende"):
                st.session_state.current_step += 1
                st.experimental_rerun()

def render_business_side_selection():
    st.header("Selecteer de bedrijfskant")
    for side in BUSINESS_SIDES:
        if card(title=side, text="", key=side):
            st.session_state.business_side = side
            st.session_state.current_step += 1
            st.experimental_rerun()

def render_department_selection():
    st.header("Selecteer de afdeling")
    if st.session_state.business_side:
        for dept in DEPARTMENTS[st.session_state.business_side]:
            if card(title=dept, text="", key=dept):
                st.session_state.department = dept
                st.session_state.current_step += 1
                st.experimental_rerun()
    else:
        st.warning("Selecteer eerst een bedrijfskant.")

def render_prompt_selection():
    st.header("Selecteer de prompt")
    if st.session_state.department:
        for prompt in PROMPTS[st.session_state.department]:
            if card(title=prompt, text="", key=prompt):
                st.session_state.prompt = prompt
                st.session_state.current_step += 1
                st.experimental_rerun()
    else:
        st.warning("Selecteer eerst een afdeling.")

def render_input_method_selection():
    st.header("Selecteer de invoermethode")
    for method in INPUT_METHODS:
        if card(title=method, text="", key=method):
            st.session_state.input_method = method
            st.session_state.current_step += 1
            st.experimental_rerun()

def render_summary():
    st.header("Samenvatting")
    if st.session_state.input_method == "Voer tekst in of plak tekst":
        st.session_state.input_text = st.text_area("Voer tekst in:", value=st.session_state.input_text, height=200)
        if st.button("Samenvatten"):
            with st.spinner("Samenvatting maken..."):
                result = run_summarization(st.session_state.input_text, st.session_state.prompt)
                if result["error"] is None:
                    st.session_state.summary = result["summary"]
                    update_gesprekslog(st.session_state.input_text, result["summary"])
                    st.success("Samenvatting voltooid!")
                else:
                    st.error(f"Er is een fout opgetreden: {result['error']}")
    elif st.session_state.input_method in ["Upload audio", "Neem audio op"]:
        process_audio_input(st.session_state.input_method)
    elif st.session_state.input_method == "Upload tekst":
        uploaded_file = st.file_uploader("Kies een bestand", type=['txt', 'docx', 'pdf'])
        if uploaded_file:
            st.session_state.transcript = process_uploaded_file(uploaded_file)
            with st.spinner("Samenvatting maken..."):
                result = run_summarization(st.session_state.transcript, st.session_state.prompt)
                if result["error"] is None:
                    st.session_state.summary = result["summary"]
                    update_gesprekslog(st.session_state.transcript, result["summary"])
                    st.success("Samenvatting voltooid!")
                else:
                    st.error(f"Er is een fout opgetreden: {result['error']}")

    if st.session_state.summary:
        display_summary(st.session_state.summary)

def main():
    setup_page_style()
    initialize_session_state()
    render_wizard()

if __name__ == "__main__":
    main()