import streamlit as st
import os
from st_copy_to_clipboard import st_copy_to_clipboard
from streamlit_antd.tabs import st_antd_tabs
from streamlit_antd.cascader import st_antd_cascader
from streamlit_antd.result import Action, st_antd_result
from streamlit_antd.breadcrumb import st_antd_breadcrumb
from streamlit_antd.cards import Action as CardAction, Item, st_antd_cards
from ui.components import display_transcript, display_summary, display_text_input, display_file_uploader
from services.email_service import send_feedback_email
from services.summarization_service import run_summarization
from utils.audio_processing import process_audio_input as utils_process_audio_input
from utils.file_processing import process_uploaded_file
from utils.text_processing import update_gesprekslog

from streamlit_extras.switch_page_button import switch_page
from streamlit_extras.colored_header import colored_header
from streamlit_extras.add_vertical_space import add_vertical_space
from streamlit_extras.stylable_container import stylable_container


def setup_page_style():
    st.set_page_config(page_title="Gesprekssamenvatter", page_icon="🎙️", layout="wide")
    st.markdown("""
    <style>
    .stApp {
        background-color: #ffffff;
    }
    .stButton>button {
        width: 100%;
        height: 3em;
        background-color: #4CAF50;
        color: white;
        border: none;
        border-radius: 5px;
        font-size: 16px;
    }
    .stButton>button:hover {
        background-color: #45a049;
    }
    .stProgress > div > div > div > div {
        background-color: #4CAF50;
    }
    </style>
    """, unsafe_allow_html=True)


def initialize_session_state():
    defaults = {
        'summary': "",
        'summary_versions': [],
        'current_version_index': -1,
        'business_side': "",
        'department': "",
        'prompt': "",
        'input_method': "",
        'input_text': "",
        'transcript': "",
        'gesprekslog': [],
        'product_info': "",
        'selected_products': [],
        'transcription_done': False,
        'summarization_done': False,
        'processing_complete': False,
        'current_step': 0,
        'user_name': "",
        'PROMPTS_DIR': os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'prompts')),
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def render_prompt_selection():
    st.header("Selecteer een prompt")

    # List all prompts in the prompts directory recursively
    prompt_files = []
    for root, dirs, files in os.walk(st.session_state.PROMPTS_DIR):
        for file in files:
            if file.endswith('.txt'):
                relative_path = os.path.relpath(os.path.join(root, file), st.session_state.PROMPTS_DIR)
                prompt_files.append(relative_path.replace('\\', '/'))  # Normalize path for all OS

    # Let the user select a prompt file
    selected_prompt = st.selectbox("Selecteer een prompt", prompt_files)

    if st.button("Bevestig prompt"):
        st.session_state.conversation_type = os.path.splitext(os.path.basename(selected_prompt))[0]
        st.session_state.prompt_path = os.path.join(st.session_state.PROMPTS_DIR, selected_prompt)
        st.session_state.current_step = 1  # Move to the next step
        st.rerun()


def render_input_method_selection():
    st.header("Selecteer de invoermethode")
    
    for method in st.session_state.INPUT_METHODS:
        if st.button(method, key=f"input_method_{method}"):
            st.session_state.input_method = method
            st.session_state.current_step = 2
            st.rerun()


def render_summary():
    colored_header("Samenvatting", description="Bekijk en bewerk de gegenereerde samenvatting")
    
    if st.session_state.input_method == "Voer tekst in of plak tekst":
        st.session_state.input_text = display_text_input("Voer tekst in:", value=st.session_state.input_text, height=200)
        if st.button("Samenvatten"):
            with st.spinner("Samenvatting maken..."):
                result = run_summarization(st.session_state.input_text, st.session_state.conversation_type, st.session_state.user_name)
                handle_summarization_result(result, st.session_state.input_text)

    elif st.session_state.input_method in ["Upload audio", "Neem audio op"]:
        handle_audio_input()

    elif st.session_state.input_method == "Upload tekst":
        uploaded_file = display_file_uploader("Kies een bestand", type=['txt', 'docx', 'pdf'])
        if uploaded_file:
            with st.spinner("Samenvatting maken..."):
                st.session_state.transcript = process_uploaded_file(uploaded_file)
                result = run_summarization(st.session_state.transcript, st.session_state.conversation_type, st.session_state.user_name)
                handle_summarization_result(result, st.session_state.transcript)

    if st.session_state.get('summary'):
        st.markdown("### Gegenereerde samenvatting:")
        st.markdown(st.session_state.summary)
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Download als Word"):
                doc = create_word_document(st.session_state.summary)
                st.download_button(
                    label="Download Word bestand",
                    data=doc,
                    file_name="samenvatting.docx",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                )
        with col2:
            st_copy_to_clipboard(st.session_state.summary, "Kopieer naar klembord")
        
        # Render feedback form only after the summary is generated
        render_feedback_form()


def handle_summarization_result(result, input_text):
    if result["error"] is None:
        st.session_state.summary = result["summary"]
        update_gesprekslog(input_text, result["summary"])
        st.success("Samenvatting voltooid!")
    else:
        st.error(f"Er is een fout opgetreden: {result['error']}")
    
    if st.button("Probeer opnieuw"):
        st.rerun()


def handle_audio_input():
    try:
        result = utils_process_audio_input(st.session_state.input_method, st.session_state.prompt, st.session_state.user_name)
        if result:
            handle_summarization_result(result, result.get("transcript", ""))
    except Exception as e:
        st.error(f"Er is een fout opgetreden bij het verwerken van de audio: {str(e)}")
        if st.button("Probeer opnieuw"):
            st.rerun()


def render_feedback_form():
    st.subheader("Geef feedback")
    
    with st.form(key="feedback_form"):
        user_first_name = st.text_input("Uw voornaam (verplicht bij feedback):")
        feedback = st.radio("Was dit antwoord nuttig?", ["Positief", "Negatief"])
        additional_feedback = st.text_area("Laat aanvullende feedback achter:")
        submit_button = st.form_submit_button(label="Verzenden")

        if submit_button:
            if not user_first_name:
                st.warning("Voornaam is verplicht bij het geven van feedback.")
            else:
                success = send_feedback_email(
                    transcript=st.session_state.get('transcript', ''),
                    summary=st.session_state.get('summary', ''),
                    feedback=feedback,
                    additional_feedback=additional_feedback,
                    user_first_name=user_first_name
                )
                if success:
                    st.success("Bedankt voor uw feedback!")
                else:
                    st.error("Er is een fout opgetreden bij het verzenden van de feedback. Probeer het later opnieuw.")


def render_wizard():
    setup_page_style()
    initialize_session_state()

    if st.session_state.current_step == 0:
        render_prompt_selection()
    elif st.session_state.current_step == 1:
        render_input_method_selection()
    elif st.session_state.current_step == 2:
        render_summary()

def render_conversation_history():
    st.subheader("Laatste vijf gesprekken")
    for i, gesprek in enumerate(st.session_state.get('gesprekslog', [])[:5]):
        with st.expander(f"Gesprek {i+1} op {gesprek['time']}"):
            st.markdown("**Transcript:**")
            display_transcript(gesprek["transcript"])
            st.markdown("**Samenvatting:**")
            st.markdown(gesprek["summary"])

def main():
    render_wizard()


if __name__ == "__main__":
    main()
