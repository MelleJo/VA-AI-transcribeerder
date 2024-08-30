# src/prompt_module.py

import streamlit as st
from src import ui_components, utils

def render_prompt_selection():
    st.header("Step 2: Prompt Selection")
    
    prompt_names = utils.get_prompt_names()
    if not prompt_names:
        st.warning("No prompts found. Please check the prompts directory.")
        return

    selected_prompt_name = st.selectbox("Select a prompt:", prompt_names, key="prompt_selector")
    
    if selected_prompt_name:
        prompt_content = utils.get_prompt_content(selected_prompt_name)
        st.markdown("### Selected Prompt")
        st.text_area("Prompt Content", value=prompt_content, height=150, disabled=True)
        
        if st.button("Use This Prompt"):
            st.session_state.selected_prompt = prompt_content
            st.success(f"Selected prompt: {selected_prompt_name}")
            st.rerun()

    if st.session_state.get('selected_prompt'):
        st.markdown("### Currently Selected Prompt")
        st.text_area("", value=st.session_state.selected_prompt, height=150, disabled=True)