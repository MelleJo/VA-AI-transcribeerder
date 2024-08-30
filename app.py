# app.py

import streamlit as st
from src import config, input_module, summary_module, output_module, ui_components, utils

def main():
    st.set_page_config(page_title="Gesprekssamenvatter API", layout="wide")
    ui_components.apply_custom_css()

    st.title("Gesprekssamenvatter API")

    # Initialize session state
    if 'step' not in st.session_state:
        st.session_state.step = 1
    if 'input_text' not in st.session_state:
        st.session_state.input_text = ""
    if 'summary' not in st.session_state:
        st.session_state.summary = ""
    if 'selected_prompt' not in st.session_state:
        st.session_state.selected_prompt = None

    # Navigation
    steps = ["Invoer", "Samenvatting Genereren", "Uitvoer"]
    st.progress((st.session_state.step - 1) / (len(steps) - 1))

    if st.session_state.step == 1:
        input_module.render_input_step()
    elif st.session_state.step == 2:
        summary_module.render_summary_generation()
    elif st.session_state.step == 3:
        output_module.render_output()

    # Navigation buttons
    col1, col2, col3 = st.columns([1, 2, 1])
    with col1:
        if st.session_state.step > 1:
            if st.button("Vorige"):
                st.session_state.step -= 1
                st.rerun()

    with col3:
        if st.session_state.step < len(steps):
            if st.button("Volgende"):
                st.session_state.step += 1
                st.rerun()

if __name__ == "__main__":
    main()