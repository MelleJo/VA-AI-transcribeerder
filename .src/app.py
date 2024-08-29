import streamlit as st
from streamlit_option_menu import option_menu
from streamlit_card import card
import os
import sys
import json
from openai_service import perform_gpt4_operation
from utils.audio_processing import process_audio_input
from services.summarization_service import run_summarization
from utils.file_processing import process_uploaded_file
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

def setup_page_style():
    st.set_page_config(page_title="Gesprekssamenvatter", page_icon="🎙️", layout="wide")
    st.markdown("""
    <style>
    .main {
        background-color: #f8f9fa;
        color: #212529;
        font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
    }
    .stButton>button {
        background-color: #007bff;
        color: white;
        border: none;
        padding: 0.5rem 1rem;
        text-align: center;
        text-decoration: none;
        display: inline-block;
        font-size: 1rem;
        margin: 0.5rem 0;
        cursor: pointer;
        border-radius: 0.25rem;
        transition: all 0.3s ease;
    }
    .stButton>button:hover {
        background-color: #0056b3;
        box-shadow: 0 4px 8px rgba(0, 123, 255, 0.3);
    }
    .summary-box {
        background-color: #ffffff;
        border-radius: 0.5rem;
        padding: 1.5rem;
        margin: 1rem 0;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        transition: all 0.3s ease;
    }
    .summary-box:hover {
        box-shadow: 0 6px 12px rgba(0, 0, 0, 0.15);
        transform: translateY(-2px);
    }
    .summary-box h3 {
        color: #007bff;
        border-bottom: 2px solid #007bff;
        padding-bottom: 0.5rem;
        margin-bottom: 1rem;
    }
    .content {
        font-size: 1rem;
        line-height: 1.6;
        color: #343a40;
    }
    .transcript-box {
        background-color: #e9ecef;
        border-radius: 0.25rem;
        padding: 1rem;
        margin-bottom: 1rem;
    }
    .copy-button {
        text-align: center;
        margin-top: 1rem;
    }
    .stProgress > div > div > div > div {
        background-color: #007bff;
    }
    .stSelectbox {
        color: #495057;
    }
    .stSelectbox > div > div {
        background-color: #ffffff;
        border-radius: 0.25rem;
    }
    .stRadio > div {
        background-color: #ffffff;
        border-radius: 0.25rem;
        padding: 0.5rem;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
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
        'current_step': 0,
        'user_name': "",
        'PROMPTS_DIR': PROMPTS_DIR
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

def render_wizard():
    st.title("Gesprekssamenvatter")

    steps = ["Bedrijfsonderdeel", "Afdeling", "Prompt", "Invoermethode", "Samenvatting"]
    selected_step = option_menu(
        menu_title=None,
        options=steps,
        icons=["building", "people", "chat-left-text", "input-cursor-text", "file-text"],
        menu_icon="cast",
        default_index=st.session_state.current_step,
        orientation="horizontal",
        styles={
            "container": {"padding": "0!important", "background-color": "#f8f9fa"},
            "icon": {"color": "#007bff", "font-size": "20px"},
            "nav-link": {
                "font-size": "16px",
                "text-align": "center",
                "margin": "0px",
                "--hover-color": "#eee",
            },
            "nav-link-selected": {"background-color": "#007bff", "color": "white"},
        }
    )

    st.session_state.current_step = steps.index(selected_step)

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

    col1, col2, col3 = st.columns([1, 1, 1])
    with col1:
        if st.session_state.current_step > 0:
            if st.button("Vorige", key="prev_button"):
                st.session_state.current_step -= 1
                st.rerun()
    with col3:
        if st.session_state.current_step < len(steps) - 1:
            if st.button("Volgende", key="next_button"):
                st.session_state.current_step += 1
                st.rerun()

def render_business_side_selection():
    st.header("Selecteer het bedrijfsonderdeel")

    if 'user_name' not in st.session_state:
        st.session_state.user_name = ""

    user_name = st.text_input("Uw naam (optioneel):", value=st.session_state.user_name, key="user_name_input")

    if user_name != st.session_state.user_name:
        st.session_state.user_name = user_name

    cols = st.columns(3)
    for i, business_side in enumerate(BUSINESS_SIDES):
        with cols[i % 3]:
            if card(title=business_side, text="", key=business_side):
                st.session_state.business_side = business_side
                st.session_state.current_step += 1
                st.rerun()

def render_department_selection():
    st.header("Selecteer de afdeling")
    if st.session_state.business_side:
        cols = st.columns(3)
        for i, dept in enumerate(DEPARTMENTS.keys()):
            with cols[i % 3]:
                if card(title=dept, text="", key=dept):
                    st.session_state.department = dept
                    st.session_state.current_step += 1
                    st.rerun()
    else:
        st.warning("Selecteer eerst een bedrijfsonderdeel.")

def render_prompt_selection():
    st.header("Selecteer de prompt")
    if st.session_state.department:
        cols = st.columns(3)
        for i, prompt in enumerate(DEPARTMENTS[st.session_state.department]):
            with cols[i % 3]:
                if card(title=prompt, text="", key=prompt):
                    st.session_state.prompt = prompt
                    st.session_state.current_step += 1
                    st.rerun()
    else:
        st.warning("Selecteer eerst een afdeling.")

def render_input_method_selection():
    st.header("Selecteer de invoermethode")
    cols = st.columns(2)
    for i, method in enumerate(INPUT_METHODS):
        with cols[i % 2]:
            if card(title=method, text="", key=method):
                st.session_state.input_method = method
                st.session_state.current_step += 1
                st.rerun()

def render_summary():
    st.header("Samenvatting")
    if st.session_state.input_method == "Voer tekst in of plak tekst":
        st.session_state.input_text = st.text_area("Voer tekst in:", value=st.session_state.input_text, height=200)
        if st.button("Samenvatten"):
            with st.spinner("Samenvatting maken..."):
                result = run_summarization(st.session_state.input_text, st.session_state.prompt, st.session_state.user_name)
                if result["error"] is None:
                    st.session_state.summary = result["summary"]
                    update_gesprekslog(st.session_state.input_text, result["summary"])
                    st.success("Samenvatting voltooid!")
                else:
                    st.error(f"Er is een fout opgetreden: {result['error']}")
                    st.error("Controleer of het juiste prompt bestand aanwezig is in de 'prompts' map.")
    elif st.session_state.input_method in ["Upload audio", "Neem audio op"]:
        result = process_audio_input(st.session_state.input_method, st.session_state.prompt, st.session_state.user_name)
        if result and result["error"] is None:
            st.session_state.summary = result["summary"]
            st.success("Samenvatting voltooid!")
        elif result:
            st.error(f"Er is een fout opgetreden: {result['error']}")
    elif st.session_state.input_method == "Upload tekst":
        uploaded_file = st.file_uploader("Kies een bestand", type=['txt', 'docx', 'pdf'])
        if uploaded_file:
            st.session_state.transcript = process_uploaded_file(uploaded_file)
            with st.spinner("Samenvatting maken..."):
                result = run_summarization(st.session_state.transcript, st.session_state.prompt, st.session_state.user_name)
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