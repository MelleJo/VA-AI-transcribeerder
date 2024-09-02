# src/prompt_module.py

import streamlit as st
from src import utils

def render_prompt_selection():
    st.header("Stap 1: Selecteer instructies")
    
    prompts = utils.get_prompt_names()  # This now excludes the base prompt
    selected_prompt = st.selectbox("Kies een instructieset:", prompts)
    
    if selected_prompt:
        st.session_state.selected_prompt = selected_prompt