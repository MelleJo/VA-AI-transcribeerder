# src/input_module.py

import streamlit as st
from src import config
from src.utils import transcribe_audio, process_text_file

def render_input_step():
    st.header("Step 1: Input")
    
    input_method = st.radio("Choose input method:", 
                            ["Upload audio", "Record audio", "Write/paste text", "Upload text file"])
    
    if input_method == "Upload audio":
        audio_file = st.file_uploader("Upload an audio file", type=config.ALLOWED_AUDIO_TYPES)
        if audio_file:
            st.session_state.input_text = transcribe_audio(audio_file)
            st.success("Audio transcribed successfully!")
    
    elif input_method == "Record audio":
        st.warning("Audio recording feature is not implemented yet.")
        # Implement audio recording logic here
    
    elif input_method == "Write/paste text":
        st.session_state.input_text = st.text_area("Enter or paste your text here:", height=300)
    
    elif input_method == "Upload text file":
        text_file = st.file_uploader("Upload a text file", type=config.ALLOWED_TEXT_TYPES)
        if text_file:
            st.session_state.input_text = process_text_file(text_file)
            st.success("Text file processed successfully!")
    
    if st.session_state.input_text:
        st.markdown("### Input Preview")
        st.text_area("", value=st.session_state.input_text[:500] + "...", height=150, disabled=True)