import streamlit as st
from src import config, prompt_module, input_module, summary_and_output_module, ui_components, history_module
from src.utils import post_process_grammar_check, format_currency, load_prompts, get_prompt_content, transcribe_audio, process_text_file
import logging
import os
from openai import OpenAI

logging.getLogger('watchdog').setLevel(logging.ERROR)

def load_css():
    css_path = os.path.join('static', 'styles.css')
    with open(css_path) as f:
        return f'<style>{f.read()}</style>'

def main():
    st.set_page_config(page_title="Gesprekssamenvatter AI", layout="wide")

    # Apply custom CSS
    st.markdown(load_css(), unsafe_allow_html=True)
    ui_components.apply_custom_css()

    # Initialize OpenAI client
    client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

    # Initialize session state
    if 'step' not in st.session_state:
        st.session_state.step = 'prompt_selection'
    if 'selected_prompt' not in st.session_state:
        st.session_state.selected_prompt = None
    if 'input_text' not in st.session_state:
        st.session_state.input_text = ""
    if 'summary' not in st.session_state:
        st.session_state.summary = ""

    # Load prompts
    prompts = load_prompts()
    st.session_state.base_prompt = prompts.get('base_prompt.txt', '')

    st.markdown("<h1 class='main-title'>Gesprekssamenvatter AI</h1>", unsafe_allow_html=True)

    if st.session_state.step == 'prompt_selection':
        render_prompt_selection()
    elif st.session_state.step == 'input_selection':
        render_input_selection()
    elif st.session_state.step == 'results':
        render_results()

def render_prompt_selection():
    st.markdown("<h2 class='section-title'>Wat wil je doen?</h2>", unsafe_allow_html=True)
    
    prompt_categories = {
        "Zakelijk": ["Vergadernotulen", "Klantgesprek", "Presentatie"],
        "Persoonlijk": ["Dagboek", "Ideeën", "Reisverslag"],
        "Educatief": ["Lezing", "Studiemateriaal", "Onderzoeksnotities"]
    }

    selected_category = st.selectbox("Kies een categorie", list(prompt_categories.keys()))
    
    col1, col2, col3 = st.columns(3)
    for i, prompt in enumerate(prompt_categories[selected_category]):
        with [col1, col2, col3][i % 3]:
            if ui_components.prompt_card(prompt):
                st.session_state.selected_prompt = prompt
                st.session_state.step = 'input_selection'
                st.experimental_rerun()

def render_input_selection():
    st.markdown(f"<h2 class='section-title'>Invoermethode voor: {st.session_state.selected_prompt}</h2>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if ui_components.input_method_card("Opnemen", "microphone"):
            st.session_state.input_method = "record"
            input_module.render_audio_input()
    
    with col2:
        if ui_components.input_method_card("Uploaden", "paperclip"):
            st.session_state.input_method = "upload"
            uploaded_file = st.file_uploader("Upload een audio- of tekstbestand", type=config.ALLOWED_AUDIO_TYPES + config.ALLOWED_TEXT_TYPES)
            if uploaded_file:
                st.session_state.uploaded_file = uploaded_file
    
    with col3:
        if ui_components.input_method_card("Typen", "pencil"):
            st.session_state.input_method = "type"
            st.session_state.input_text = st.text_area("Voer tekst in:", height=200)

    if st.button("Begin transcriptie en samenvatting", key="start_process_button"):
        process_input_and_generate_summary()

def process_input_and_generate_summary():
    with st.spinner("Bezig met verwerken..."):
        if st.session_state.input_method == "upload" and 'uploaded_file' in st.session_state:
            if st.session_state.uploaded_file.type.startswith('audio/'):
                st.session_state.input_text = transcribe_audio(st.session_state.uploaded_file)
            else:
                st.session_state.input_text = process_text_file(st.session_state.uploaded_file)
        elif st.session_state.input_method == "record" and 'audio_data' in st.session_state:
            st.session_state.input_text = transcribe_audio(st.session_state.audio_data)

        if st.session_state.input_text and st.session_state.selected_prompt:
            st.session_state.summary = summary_and_output_module.generate_summary(
                st.session_state.input_text,
                st.session_state.base_prompt,
                get_prompt_content(st.session_state.selected_prompt)
            )
            st.session_state.step = 'results'
            st.experimental_rerun()

def render_results():
    col1, col2 = st.columns([3, 2])
    
    with col1:
        st.markdown("<h2 class='section-title'>Samenvatting</h2>", unsafe_allow_html=True)
        summary_and_output_module.render_summary()
    
    with col2:
        st.markdown("<h2 class='section-title'>Chat</h2>", unsafe_allow_html=True)
        summary_and_output_module.render_chat_interface()

    with st.expander("Bekijk/Bewerk Transcript"):
        edited_transcript = st.text_area("Transcript:", value=st.session_state.input_text, height=300)
        if edited_transcript != st.session_state.input_text:
            st.session_state.input_text = edited_transcript
            if st.button("Genereer opnieuw"):
                st.session_state.summary = summary_and_output_module.generate_summary(
                    st.session_state.input_text,
                    st.session_state.base_prompt,
                    get_prompt_content(st.session_state.selected_prompt)
                )
                st.experimental_rerun()

    if st.button("Terug naar begin", key="back_to_start_button"):
        st.session_state.step = 'prompt_selection'
        st.session_state.selected_prompt = None
        st.session_state.input_text = ""
        st.session_state.summary = ""
        st.experimental_rerun()

if __name__ == "__main__":
    main()