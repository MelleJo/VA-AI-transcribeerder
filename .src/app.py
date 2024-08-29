import streamlit as st
from streamlit_antd.tabs import st_antd_tabs
from streamlit_antd.cascader import st_antd_cascader
from streamlit_antd.result import Action, st_antd_result
from streamlit_antd.breadcrumb import st_antd_breadcrumb
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
    event = st_antd_tabs([{"Label": step} for step in steps], key="wizard_tabs")
    
    if event:
        st.session_state.current_step = steps.index(event['payload']['Label'])

    breadcrumb_items = [{"Label": step} for step in steps[:st.session_state.current_step + 1]]
    st_antd_breadcrumb(breadcrumb_items, key="breadcrumb")

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
            if st.button("Vorige"):
                st.session_state.current_step -= 1
                st.experimental_rerun()
    with col3:
        if st.session_state.current_step < len(steps) - 1:
            if st.button("Volgende"):
                st.session_state.current_step += 1
                st.experimental_rerun()

def render_business_side_selection():
    st.header("Selecteer het bedrijfsonderdeel")
    
    if 'user_name' not in st.session_state:
        st.session_state.user_name = ""
    
    user_name = st.text_input("Uw naam (optioneel):", value=st.session_state.user_name, key="user_name_input")
    
    if user_name != st.session_state.user_name:
        st.session_state.user_name = user_name

    selected = st_antd_cascader(
        [{"value": side, "label": side} for side in BUSINESS_SIDES],
        key="business_side_cascader"
    )
    
    if selected:
        st.session_state.business_side = selected[0]
        st.session_state.current_step += 1
        st.experimental_rerun()

def render_department_selection():
    st.header("Selecteer de afdeling")
    if st.session_state.business_side:
        selected = st_antd_cascader(
            [{"value": dept, "label": dept} for dept in DEPARTMENTS.keys()],
            key="department_cascader"
        )
        if selected:
            st.session_state.department = selected[0]
            st.session_state.current_step += 1
            st.experimental_rerun()
    else:
        st.warning("Selecteer eerst een bedrijfsonderdeel.")

def render_prompt_selection():
    st.header("Selecteer de prompt")
    if st.session_state.department:
        selected = st_antd_cascader(
            [{"value": prompt, "label": prompt} for prompt in DEPARTMENTS[st.session_state.department]],
            key="prompt_cascader"
        )
        if selected:
            st.session_state.prompt = selected[0]
            st.session_state.current_step += 1
            st.experimental_rerun()
    else:
        st.warning("Selecteer eerst een afdeling.")

def render_input_method_selection():
    st.header("Selecteer de invoermethode")
    selected = st_antd_cascader(
        [{"value": method, "label": method} for method in INPUT_METHODS],
        key="input_method_cascader"
    )
    if selected:
        st.session_state.input_method = selected[0]
        st.session_state.current_step += 1
        st.experimental_rerun()

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
                    st_antd_result(
                        "Samenvatting voltooid!",
                        "De samenvatting is succesvol gegenereerd.",
                        [Action("show", "Toon samenvatting", primary=True)]
                    )
                else:
                    st_antd_result(
                        "Er is een fout opgetreden",
                        result["error"],
                        [Action("retry", "Probeer opnieuw")]
                    )
    elif st.session_state.input_method in ["Upload audio", "Neem audio op"]:
        result = process_audio_input(st.session_state.input_method, st.session_state.prompt, st.session_state.user_name)
        if result and result["error"] is None:
            st.session_state.summary = result["summary"]
            st_antd_result(
                "Samenvatting voltooid!",
                "De samenvatting is succesvol gegenereerd.",
                [Action("show", "Toon samenvatting", primary=True)]
            )
        elif result:
            st_antd_result(
                "Er is een fout opgetreden",
                result["error"],
                [Action("retry", "Probeer opnieuw")]
            )
    elif st.session_state.input_method == "Upload tekst":
        uploaded_file = st.file_uploader("Kies een bestand", type=['txt', 'docx', 'pdf'])
        if uploaded_file:
            st.session_state.transcript = process_uploaded_file(uploaded_file)
            with st.spinner("Samenvatting maken..."):
                result = run_summarization(st.session_state.transcript, st.session_state.prompt, st.session_state.user_name)
                if result["error"] is None:
                    st.session_state.summary = result["summary"]
                    update_gesprekslog(st.session_state.transcript, result["summary"])
                    st_antd_result(
                        "Samenvatting voltooid!",
                        "De samenvatting is succesvol gegenereerd.",
                        [Action("show", "Toon samenvatting", primary=True)]
                    )
                else:
                    st_antd_result(
                        "Er is een fout opgetreden",
                        result["error"],
                        [Action("retry", "Probeer opnieuw")]
                    )

    if st.session_state.summary:
        display_summary(st.session_state.summary)

def main():
    setup_page_style()
    initialize_session_state()
    render_wizard()

if __name__ == "__main__":
    main()