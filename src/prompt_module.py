# src/prompt_module.py

import streamlit as st
from src import ui_components, utils

def render_prompt_selection():
    st.header("Stap 1: Prompt Selectie")
    
    prompts = utils.load_prompts()
    selected_prompt = st.selectbox("Kies een prompt:", list(prompts.keys()))
    
    if selected_prompt:
        st.session_state.selected_prompt = prompts[selected_prompt]
        st.markdown("### Geselecteerde Prompt")
        st.markdown(st.session_state.selected_prompt)

    if st.button("Bevestig Prompt"):
        if st.session_state.selected_prompt:
            st.session_state.step = 2
            st.rerun()
        else:
            st.warning("Selecteer eerst een prompt voordat u doorgaat.")