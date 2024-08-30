# src/input_module.py

import streamlit as st
from src import config
from src.utils import transcribe_audio, process_text_file

def render_input_step():
    st.header("Stap 1: Invoer")
    
    input_method = st.radio("Kies invoermethode:", 
                            ["Audio uploaden", "Audio opnemen", "Tekst schrijven/plakken", "Tekstbestand uploaden"])
    
    if input_method == "Audio uploaden":
        audio_file = st.file_uploader("Upload een audiobestand", type=config.ALLOWED_AUDIO_TYPES)
        if audio_file:
            st.session_state.input_text = transcribe_audio(audio_file)
            st.success("Audio succesvol getranscribeerd!")
    
    elif input_method == "Audio opnemen":
        st.warning("Audio opname functie is nog niet geïmplementeerd.")
        # Implement audio recording logic here
    
    elif input_method == "Tekst schrijven/plakken":
        st.session_state.input_text = st.text_area("Voer hier uw tekst in of plak deze:", height=300)
    
    elif input_method == "Tekstbestand uploaden":
        text_file = st.file_uploader("Upload een tekstbestand", type=config.ALLOWED_TEXT_TYPES)
        if text_file:
            st.session_state.input_text = process_text_file(text_file)
            st.success("Tekstbestand succesvol verwerkt!")
    
    if st.session_state.input_text:
        st.markdown("### Invoer Voorbeeld")
        st.text_area("", value=st.session_state.input_text[:500] + "...", height=150, disabled=True)