# src/prompt_module.py

import streamlit as st
from src import utils

def render_prompt_selection():
    st.header("Stap 1: Selecteer instructies")
    
    prompts = utils.load_prompts()
    selected_prompt = st.selectbox("Kies een intstructieset:", list(prompts.keys()))
    
    if selected_prompt:
        st.session_state.selected_prompt = prompts[selected_prompt]

    if st.button("Bevestig instructieset"):
        if st.session_state.selected_prompt:
            st.session_state.step = 2
            st.rerun()
        else:
            st.warning("Selecteer eerst een instructieset voordat u doorgaat.")