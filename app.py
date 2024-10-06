# app.py

import streamlit as st
from src import input_module, summary_and_output_module
from src.utils import get_prompt_content, load_prompts
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def main():
    st.set_page_config(page_title="Gesprekssamenvatter AI", layout="wide")
    st.title("Gesprekssamenvatter AI")

    if 'step' not in st.session_state:
        st.session_state.step = 'input'

    if 'base_prompt' not in st.session_state:
        prompts = load_prompts()
        st.session_state.base_prompt = prompts.get('base_prompt.txt', '')

    if st.session_state.step == 'input':
        handle_input()
    elif st.session_state.step == 'summary':
        generate_summary()
    elif st.session_state.step == 'display':
        display_summary()

def handle_input():
    st.header("Stap 1: Voer gespreksinhoud in")
    
    prompt_options = [p for p in load_prompts().keys() if p != 'base_prompt.txt']
    selected_prompt = st.selectbox("Kies een prompt:", prompt_options)
    st.session_state.selected_prompt = selected_prompt

    input_text = input_module.render_input_step()
    
    if input_text:
        st.session_state.input_text = input_text
        st.session_state.step = 'summary'
        st.rerun()

def generate_summary():
    st.header("Stap 2: Samenvatting genereren")
    
    with st.spinner("Samenvatting wordt gegenereerd..."):
        summary = summary_and_output_module.generate_summary(
            st.session_state.input_text,
            st.session_state.base_prompt,
            get_prompt_content(st.session_state.selected_prompt)
        )
        
        if summary:
            st.session_state.summary = summary
            st.session_state.step = 'display'
            st.rerun()
        else:
            st.error("Er is een fout opgetreden bij het genereren van de samenvatting.")
            st.session_state.step = 'input'

def display_summary():
    st.header("Stap 3: Samenvatting")
    st.markdown(st.session_state.summary)
    
    if st.button("Nieuwe samenvatting maken"):
        st.session_state.step = 'input'
        st.session_state.input_text = ""
        st.session_state.summary = ""
        st.rerun()

if __name__ == "__main__":
    main()