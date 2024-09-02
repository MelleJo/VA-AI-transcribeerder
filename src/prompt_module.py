# src/prompt_module.py

import streamlit as st
from src import utils

def render_prompt_selection():
    st.header("Stap 1: Selecteer instructies")
    
    prompts = utils.load_prompts()
    selected_prompt = st.selectbox("Kies een instructieset:", list(prompts.keys()))
    
    if selected_prompt:
        st.session_state.selected_prompt = prompts[selected_prompt]