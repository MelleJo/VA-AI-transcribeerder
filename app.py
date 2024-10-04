# app.py

import streamlit as st
from src import config, prompt_module, input_module, summary_and_output_module, ui_components
from src.utils import post_process_grammar_check, format_currency, load_prompts
import logging
import os
import uuid
from openai import OpenAI

logging.getLogger('watchdog').setLevel(logging.ERROR)

def load_css():
    css_path = os.path.join('static', 'styles.css')
    with open(css_path) as f:
        return f'<style>{f.read()}</style>'

def main():
    st.set_page_config(page_title="Gesprekssamenvatter AI", layout="wide")

    # Apply custom CSS
    st.markdown(load_css(), unsafe_allow_html=True)
    ui_components.apply_custom_css()

    # Initialize OpenAI client
    client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

    # Initialize session state
    if 'step' not in st.session_state:
        st.session_state.step = 1
    if 'selected_prompt' not in st.session_state:
        st.session_state.selected_prompt = None
    if 'input_text' not in st.session_state:
        st.session_state.input_text = ""
    if 'summary' not in st.session_state:
        st.session_state.summary = ""
    
    # Load prompts
    prompts = load_prompts()
    if 'base_prompt' not in st.session_state:
        st.session_state.base_prompt = prompts.get('base_prompt.txt', '')

    # Main content
    st.markdown("<h1 class='main-title'>Gesprekssamenvatter AI</h1>", unsafe_allow_html=True)

    if st.session_state.step == 1:
        render_input_options()
    elif st.session_state.step == 2:
        render_transcript_and_prompt_selection()
    elif st.session_state.step == 3:
        render_summary_and_chat()

def render_input_options():
    st.markdown("<h2 class='section-title'>Kies een invoermethode</h2>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if ui_components.ui_card_button("Uploaden", "Upload een audio- of tekstbestand"):
            st.session_state.input_method = "upload"
            st.session_state.step = 2
    
    with col2:
        if ui_components.ui_card_button("Inspreken", "Neem audio op met je microfoon"):
            st.session_state.input_method = "record"
            st.session_state.step = 2
    
    with col3:
        if ui_components.ui_card_button("Typen", "Voer tekst direct in"):
            st.session_state.input_method = "type"
            st.session_state.step = 2

def render_transcript_and_prompt_selection():
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("<h2 class='section-title'>Transcript</h2>", unsafe_allow_html=True)
        if st.session_state.input_method == "upload":
            input_module.render_upload_input()
        elif st.session_state.input_method == "record":
            input_module.render_audio_input()
        elif st.session_state.input_method == "type":
            input_module.render_text_input()
    
    with col2:
        st.markdown("<h2 class='section-title'>Kies een instructieset</h2>", unsafe_allow_html=True)
        prompt_module.render_prompt_selection()
    
    if st.session_state.input_text and st.session_state.selected_prompt:
        if ui_components.ui_button(
            label="Genereer samenvatting",
            on_click=lambda: setattr(st.session_state, 'step', 3),
            key="generate_summary_button"
        ):
            st.session_state.step = 3

def render_summary_and_chat():
    col1, col2 = st.columns([3, 2])
    
    with col1:
        st.markdown("<h2 class='section-title'>Samenvatting</h2>", unsafe_allow_html=True)
        summary_and_output_module.render_summary()
    
    with col2:
        st.markdown("<h2 class='section-title'>Chat</h2>", unsafe_allow_html=True)
        summary_and_output_module.render_chat_interface()

if __name__ == "__main__":
    main()