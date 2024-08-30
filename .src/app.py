import streamlit as st
from config import load_config
from ui.pages import render_prompt_selection, render_input_method_selection, render_summary
from ui.components import setup_page_style, initialize_session_state

def main():
    config = load_config()
    st.set_page_config(page_title="Gesprekssamenvatter", page_icon="🎙️", layout="wide")
    setup_page_style()
    initialize_session_state(config)

    if st.session_state.current_step == 0:
        render_prompt_selection()
    elif st.session_state.current_step == 1:
        render_input_method_selection()
    elif st.session_state.current_step == 2:
        render_summary()

if __name__ == "__main__":
    main()
