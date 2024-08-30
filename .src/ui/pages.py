import streamlit as st
import os
from ui.components import display_text_input, display_file_uploader
from utils.audio_processing import process_audio_input
from utils.file_processing import process_uploaded_file
from services.summarization_service import run_summarization
from utils.text_processing import update_gesprekslog

def render_prompt_selection():
    st.header("Selecteer een prompt")
    
    prompt_files = [f for f in os.listdir(st.session_state.config['PROMPTS_DIR']) if f.endswith('.txt')]
    
    if not prompt_files:
        st.error("Geen prompt bestanden gevonden in de opgegeven map.")
        return

    selected_prompt = st.selectbox("Selecteer een prompt", prompt_files)

    if st.button("Bevestig prompt"):
        st.session_state.prompt_name = os.path.splitext(selected_prompt)[0]
        st.session_state.prompt_path = os.path.join(st.session_state.config['PROMPTS_DIR'], selected_prompt)
        st.write(f"Geselecteerde prompt: {st.session_state.prompt_name}")
        st.session_state.current_step = 1
        st.rerun()

def render_input_method_selection():
    st.header("Selecteer de invoermethode")
    
    for method in st.session_state.config['INPUT_METHODS']:
        if st.button(method, key=f"input_method_{method}"):
            st.session_state.input_method = method
            st.session_state.current_step = 2
            st.rerun()

def render_summary():
    st.header("Samenvatting")
    
    if st.session_state.input_method == "Voer tekst in of plak tekst":
        handle_text_input()
    elif st.session_state.input_method in ["Upload audio", "Neem audio op"]:
        handle_audio_input()
    elif st.session_state.input_method == "Upload tekst":
        handle_file_upload()

    if st.session_state.get('summary'):
        display_summary()

def handle_text_input():
    st.session_state.input_text = display_text_input("Voer tekst in:", value=st.session_state.input_text, height=200)
    if st.button("Samenvatten"):
        with st.spinner("Samenvatting maken..."):
            result = run_summarization(st.session_state.input_text, st.session_state.prompt_name, st.session_state.user_name)
            handle_summarization_result(result, st.session_state.input_text)

def handle_audio_input():
    try:
        result = process_audio_input(st.session_state.input_method, st.session_state.prompt_path, st.session_state.user_name)
        if result:
            handle_summarization_result(result, result.get("transcript", ""))
    except Exception as e:
        st.error(f"Er is een fout opgetreden bij het verwerken van de audio: {str(e)}")
        if st.button("Probeer opnieuw"):
            st.rerun()

def handle_file_upload():
    uploaded_file = display_file_uploader("Kies een bestand", type=['txt', 'docx', 'pdf'])
    if uploaded_file:
        with st.spinner("Samenvatting maken..."):
            st.session_state.transcript = process_uploaded_file(uploaded_file)
            result = run_summarization(st.session_state.transcript, st.session_state.prompt_name, st.session_state.user_name)
            handle_summarization_result(result, st.session_state.transcript)

def handle_summarization_result(result, input_text):
    if result["error"] is None:
        st.session_state.summary = result["summary"]
        update_gesprekslog(input_text, result["summary"])
        st.success("Samenvatting voltooid!")
    else:
        st.error(f"Er is een fout opgetreden: {result['error']}")
    
    if st.button("Probeer opnieuw"):
        st.rerun()

def display_summary():
    st.markdown("### Gegenereerde samenvatting:")
    st.markdown(st.session_state.summary)
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Download als Word"):
            # Implement Word document creation and download here
            pass
    with col2:
        if st.button("Kopieer naar klembord"):
            # Implement clipboard copy functionality here
            pass
