# app.py

import streamlit as st
from src import config, input_module, prompt_module, summary_module, output_module, ui_components, utils

def main():
    st.set_page_config(page_title="Gesprekssamenvatter API", layout="wide")
    ui_components.apply_custom_css()

    st.title("Gesprekssamenvatter API")

    # Initialize session state
    if 'step' not in st.session_state:
        st.session_state.step = 1
    if 'input_text' not in st.session_state:
        st.session_state.input_text = ""
    if 'selected_prompt' not in st.session_state:
        st.session_state.selected_prompt = None
    if 'summary' not in st.session_state:
        st.session_state.summary = ""
    if 'prompts_and_departments' not in st.session_state:
        st.session_state.prompts_and_departments = utils.load_prompts_and_departments()

    # Navigation
    steps = ["Input", "Prompt Selection", "Summary Generation", "Output"]
    st.progress((st.session_state.step - 1) / (len(steps) - 1))

    if st.session_state.step == 1:
        input_module.render_input_step()
    elif st.session_state.step == 2:
        prompt_module.render_prompt_selection()
    elif st.session_state.step == 3:
        summary_module.render_summary_generation()
    elif st.session_state.step == 4:
        output_module.render_output()

    # Navigation buttons
    col1, col2, col3 = st.columns([1, 2, 1])
    with col1:
        if st.session_state.step > 1:
            if st.button("Previous"):
                st.session_state.step -= 1
                st.rerun()

    with col3:
        if st.session_state.step < len(steps):
            if st.button("Next"):
                st.session_state.step += 1
                st.rerun()

if __name__ == "__main__":
    main()