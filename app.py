import streamlit as st
from src import config, prompt_module, input_module, summary_and_output_module, ui_components, history_module
from src.utils import post_process_grammar_check, format_currency, load_prompts, get_prompt_content, transcribe_audio, process_text_file, get_prompt_names, get_prompt_content
import logging
import time
import os
from openai import OpenAI

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def initialize_session_state():
    if 'base_prompt' not in st.session_state:
        prompts = load_prompts()
        st.session_state.base_prompt = prompts.get('base_prompt.txt', '')
    if 'step' not in st.session_state:
        st.session_state.step = 'prompt_selection'
    if 'selected_prompt' not in st.session_state:
        st.session_state.selected_prompt = None
    if 'input_text' not in st.session_state:
        st.session_state.input_text = ""
    if 'summary_versions' not in st.session_state:
        st.session_state.summary_versions = []
    if 'current_version' not in st.session_state:
        st.session_state.current_version = 0
    if 'summary' not in st.session_state:
        st.session_state.summary = ""
    if 'summaries' not in st.session_state:
        st.session_state.summaries = []
    if 'is_processing' not in st.session_state:
        st.session_state.is_processing = False
    if 'uploaded_file' not in st.session_state:
        st.session_state.uploaded_file = None

def main():
    initialize_session_state()
    st.set_page_config(page_title="Gesprekssamenvatter AI", layout="wide")
    ui_components.apply_custom_css()

    st.markdown("<h1 class='main-title'>Gesprekssamenvatter AI</h1>", unsafe_allow_html=True)

    logger.debug(f"Current step: {st.session_state.step}")
    logger.debug(f"Is processing: {st.session_state.is_processing}")
    logger.debug(f"Input text length: {len(st.session_state.input_text)}")

    if st.button("Reset Application"):
        reset_app_state()
        st.rerun()

    if st.session_state.step == 'prompt_selection':
        render_prompt_selection()
    elif st.session_state.step == 'input_selection':
        render_input_selection()
    elif st.session_state.step == 'transcribing':
        transcribe_audio_file()
    elif st.session_state.step == 'processing':
        process_input_and_generate_summary()
    elif st.session_state.step == 'results':
        render_results()
    else:
        logger.error(f"Unknown step: {st.session_state.step}")
        st.error(f"Unknown step: {st.session_state.step}")
        reset_app_state()
        st.rerun()

def render_prompt_selection():
    st.markdown("<h2 class='section-title'>Wat wil je doen?</h2>", unsafe_allow_html=True)
    prompt_module.render_prompt_selection()
    if st.button("Verder ➔", key="proceed_button"):
        st.session_state.step = 'input_selection'
        st.rerun()

def render_input_selection():
    st.markdown(f"<h2 class='section-title'>Invoermethode voor: {st.session_state.selected_prompt}</h2>", unsafe_allow_html=True)
    uploaded_file = st.file_uploader("Upload een audio- of videobestand", type=config.ALLOWED_AUDIO_TYPES)
    if uploaded_file:
        st.session_state.uploaded_file = uploaded_file
        st.session_state.step = 'transcribing'
        st.rerun()

def transcribe_audio_file():
    if st.session_state.uploaded_file:
        progress_placeholder = ui_components.display_progress_animation()
        st.info("Audiobestand wordt getranscribeerd...")
        try:
            st.session_state.input_text = transcribe_audio(st.session_state.uploaded_file)
            if st.session_state.input_text:
                logger.info(f"Transcription successful. Text length: {len(st.session_state.input_text)}")
                st.session_state.is_processing = True
                st.session_state.step = 'processing'
            else:
                logger.warning("Transcription resulted in empty text")
                st.error("Transcriptie is mislukt. Probeer een ander audiobestand.")
                st.session_state.step = 'input_selection'
        except Exception as e:
            logger.exception(f"Error during audio transcription: {str(e)}")
            st.error(f"Er is een fout opgetreden tijdens de transcriptie: {str(e)}")
            st.session_state.step = 'input_selection'
        finally:
            progress_placeholder.empty()
            st.rerun()

def process_input_and_generate_summary():
    logger.debug(f"Entering process_input_and_generate_summary. is_processing: {st.session_state.is_processing}")
    if not st.session_state.is_processing:
        logger.warning("process_input_and_generate_summary called but is_processing is False")
        st.warning("No processing is currently happening. Please start over.")
        reset_app_state()
        st.rerun()
        return

    progress_placeholder = ui_components.display_progress_animation()
    
    try:
        logger.info("Generating summary")
        new_summary = summary_and_output_module.generate_summary(
            st.session_state.input_text,
            st.session_state.base_prompt,
            get_prompt_content(st.session_state.selected_prompt)
        )
        
        st.session_state.summary_versions.append(new_summary)
        st.session_state.current_version = len(st.session_state.summary_versions) - 1
        st.session_state.summary = new_summary
        st.session_state.step = 'results'
        logger.info("Summary generated successfully")
    except Exception as e:
        logger.exception("Error during summary generation")
        st.error(f"An error occurred during summary generation: {str(e)}")
        reset_app_state()
    finally:
        st.session_state.is_processing = False
        progress_placeholder.empty()
        logger.debug("Exiting process_input_and_generate_summary")
        st.rerun()

def render_results():
    summary_and_output_module.render_summary_versions()
    summary_and_output_module.render_chat_interface()

def reset_app_state():
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    initialize_session_state()

if __name__ == "__main__":
    main()