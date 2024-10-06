import streamlit as st
from src import config, prompt_module, input_module, summary_and_output_module, ui_components, history_module
from src.utils import post_process_grammar_check, format_currency, load_prompts, get_prompt_content, transcribe_audio, process_text_file, get_prompt_names, get_prompt_content
import logging
import time
import os
from openai import OpenAI

# Set up logging
logging.basicConfig(level=logging.INFO)
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

def load_css():
    css_path = os.path.join('static', 'styles.css')
    with open(css_path) as f:
        css_content = f.read()
    font_awesome = '<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/5.15.3/css/all.min.css">'
    return f'<style>{css_content}</style>{font_awesome}'

def reset_app_state():
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    initialize_session_state()

def check_state_consistency():
    if st.session_state.step == 'processing' and not st.session_state.is_processing:
        logger.warning("Inconsistent state detected: processing step with is_processing=False")
        return False
    return True

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

def handle_input_complete():
    logger.debug("handle_input_complete called")
    if st.session_state.input_text:
        logger.info(f"Input text received. Length: {len(st.session_state.input_text)}")
        st.session_state.is_processing = True
        st.session_state.step = 'processing'
        logger.debug("State updated to processing")
        st.rerun()
    else:
        logger.warning("handle_input_complete called with empty input_text")
        st.warning("No input text received. Please try again.")

def render_input_selection():
    st.markdown(f"<h2 class='section-title'>Invoermethode voor: {st.session_state.selected_prompt}</h2>", unsafe_allow_html=True)
    input_module.render_input_step(handle_input_complete)

def display_progress_animation():
    progress_placeholder = st.empty()
    progress_html = """
    <div class="full-screen-loader">
        <div class="lds-ellipsis"><div></div><div></div><div></div><div></div></div>
        <div class="progress-text">Verwerking bezig... Even geduld aub.</div>
    </div>
    """
    progress_placeholder.markdown(progress_html, unsafe_allow_html=True)
    return progress_placeholder

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

def render_summary_with_version_control():
    if st.session_state.summary_versions:
        st.markdown("<div class='version-control'>", unsafe_allow_html=True)
        col1, col2, col3 = st.columns([1, 3, 1])
        
        with col1:
            if st.button("◀ Vorige", disabled=st.session_state.current_version == 0, key="prev_version_button"):
                st.session_state.current_version -= 1
                st.session_state.summary = st.session_state.summary_versions[st.session_state.current_version]
                st.rerun()
        
        with col2:
            st.markdown(f"<p class='version-info'>Versie {st.session_state.current_version + 1} van {len(st.session_state.summary_versions)}</p>", unsafe_allow_html=True)
        
        with col3:
            if st.button("Volgende ▶", disabled=st.session_state.current_version == len(st.session_state.summary_versions) - 1, key="next_version_button"):
                st.session_state.current_version += 1
                st.session_state.summary = st.session_state.summary_versions[st.session_state.current_version]
                st.rerun()
        
        st.markdown("</div>", unsafe_allow_html=True)
        
        current_summary = st.session_state.summary_versions[st.session_state.current_version]
        st.markdown("<div class='summary-edit-area'>", unsafe_allow_html=True)
        edited_summary = st.text_area("Samenvatting:", value=current_summary, height=400, key="summary_text_area")
        st.markdown("</div>", unsafe_allow_html=True)
        
        if edited_summary != current_summary:
            if st.button("Wijzigingen opslaan", key="save_changes_button"):
                st.session_state.summary_versions.append(edited_summary)
                st.session_state.current_version = len(st.session_state.summary_versions) - 1
                st.session_state.summary = edited_summary
                st.markdown("<div class='save-success-message'>Wijzigingen opgeslagen als nieuwe versie.</div>", unsafe_allow_html=True)
                st.rerun()
    else:
        st.warning("Geen samenvatting beschikbaar.")

if __name__ == "__main__":
    main()