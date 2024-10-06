# app.py

import streamlit as st
from src import config, prompt_module, input_module, summary_and_output_module, ui_components
from src.utils import transcribe_audio, process_text_file, get_prompt_content, load_prompts
from src.state_management import AppState, initialize_session_state, transition_to_input_selection, transition_to_processing, transition_to_results, reset_state
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def main():
    initialize_session_state()
    st.set_page_config(page_title="Gesprekssamenvatter AI", layout="wide")
    ui_components.apply_custom_css()

    st.markdown("<h1 class='main-title'>Gesprekssamenvatter AI</h1>", unsafe_allow_html=True)

    if st.button("Reset Application"):
        reset_state()
        st.rerun()

    logger.debug(f"Current state: {st.session_state.state}")
    logger.debug(f"Base prompt loaded: {bool(st.session_state.base_prompt)}")

    if st.session_state.state == AppState.PROMPT_SELECTION:
        render_prompt_selection()
    elif st.session_state.state == AppState.INPUT_SELECTION:
        render_input_selection()
    elif st.session_state.state == AppState.PROCESSING:
        process_input()
    elif st.session_state.state == AppState.RESULTS:
        render_results()

def render_prompt_selection():
    st.markdown("<h2 class='section-title'>Wat wil je doen?</h2>", unsafe_allow_html=True)
    prompt_module.render_prompt_selection()
    if st.button("Verder ➔", key="proceed_button"):
        transition_to_input_selection()
        st.rerun()

def render_input_selection():
    st.markdown(f"<h2 class='section-title'>Invoermethode voor: {st.session_state.selected_prompt}</h2>", unsafe_allow_html=True)
    input_text = input_module.render_input_step()
    if input_text:
        transition_to_processing(input_text)
        st.rerun()

def process_input():
    progress_placeholder = ui_components.display_progress_animation()
    st.info("Verwerking en samenvatting worden gegenereerd...")
    
    try:
        if not st.session_state.base_prompt:
            logger.error("Base prompt is not loaded")
            raise ValueError("Base prompt is not loaded")

        summary = summary_and_output_module.generate_summary(
            st.session_state.input_text,
            st.session_state.base_prompt,
            get_prompt_content(st.session_state.selected_prompt)
        )
        
        if summary:
            transition_to_results(summary)
        else:
            st.error("Er is een fout opgetreden bij het genereren van de samenvatting.")
            reset_state()
    except Exception as e:
        logger.exception(f"Error during processing: {str(e)}")
        st.error(f"Er is een fout opgetreden: {str(e)}")
        reset_state()
    finally:
        progress_placeholder.empty()
    
    st.rerun()

def render_results():
    summary_and_output_module.render_summary_versions()
    summary_and_output_module.render_chat_interface()

if __name__ == "__main__":
    main()