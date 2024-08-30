# src/prompt_module.py

import streamlit as st
from src import ui_components, utils

def render_prompt_selection():
    st.header("Step 2: Prompt Selection")
    
    departments = utils.get_departments()
    selected_department = st.selectbox("Select a department:", departments)
    
    prompts = utils.get_prompts(selected_department)
    
    st.markdown("### Available Prompts")
    cols = st.columns(3)
    for i, (prompt_name, prompt_content) in enumerate(prompts.items()):
        with cols[i % 3]:
            if ui_components.create_card(prompt_name, prompt_content[:100] + "...", f"prompt_{i}"):
                st.session_state.selected_prompt = prompt_content
                st.success(f"Selected prompt: {prompt_name}")
                st.rerun()

    if st.session_state.selected_prompt:
        st.markdown("### Selected Prompt")
        st.text_area("", value=st.session_state.selected_prompt, height=150, disabled=True)