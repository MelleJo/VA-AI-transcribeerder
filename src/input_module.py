# src/input_module.py

import streamlit as st
from src import config
from src.utils import transcribe_audio, process_text_file
import time

def render_input_step():
    st.header("Stap 2: Invoer")
    
    if 'transcription_complete' not in st.session_state:
        st.session_state.transcription_complete = False

    input_method = st.radio("Kies invoermethode:", 
                            ["Audio uploaden", "Audio opnemen", "Tekst schrijven/plakken", "Tekstbestand uploaden"])
    
    if input_method == "Audio uploaden" and not st.session_state.transcription_complete:
        audio_file = st.file_uploader("Upload een audiobestand", type=config.ALLOWED_AUDIO_TYPES)
        if audio_file:
            with st.spinner("Audio wordt getranscribeerd..."):
                progress_bar = st.progress(0)
                status_text = st.empty()
                start_time = time.time()

                def update_progress(current, total):
                    progress = current / total
                    progress_bar.progress(progress)
                    elapsed_time = time.time() - start_time
                    estimated_total_time = elapsed_time / progress if progress > 0 else 0
                    remaining_time = estimated_total_time - elapsed_time
                    status_text.text(f"Verwerkt: {current}/{total} chunks ({progress:.1%}) - Geschatte resterende tijd: {remaining_time:.1f} seconden")

                st.session_state.input_text = transcribe_audio(audio_file, update_progress)
                progress_bar.empty()
                status_text.empty()
                if st.session_state.input_text:
                    st.success("Audio succesvol getranscribeerd!")
                    st.session_state.transcription_complete = True
                else:
                    st.error("Transcriptie is mislukt. Probeer een ander audiobestand.")
    
    elif input_method == "Audio opnemen" and not st.session_state.transcription_complete:
        st.warning("Audio opname functie is nog niet geïmplementeerd.")
        # Implement audio recording logic here
    
    elif input_method == "Tekst schrijven/plakken" and not st.session_state.transcription_complete:
        st.session_state.input_text = st.text_area("Voer hier uw tekst in of plak deze:", height=300)
        if st.session_state.input_text:
            st.session_state.transcription_complete = True
    
    elif input_method == "Tekstbestand uploaden" and not st.session_state.transcription_complete:
        text_file = st.file_uploader("Upload een tekstbestand", type=config.ALLOWED_TEXT_TYPES)
        if text_file:
            st.session_state.input_text = process_text_file(text_file)
            if st.session_state.input_text:
                st.success("Tekstbestand succesvol verwerkt!")
                st.session_state.transcription_complete = True

    if st.session_state.transcription_complete:
        st.markdown("### Transcript")
        st.session_state.input_text = st.text_area("Bewerk indien nodig:", value=st.session_state.input_text, height=300)

    if st.button("Ga naar Transcript Bewerken"):
        if st.session_state.input_text:
            st.session_state.step = 3
            st.rerun()
        else:
            st.warning("Voer eerst tekst in voordat u doorgaat.")