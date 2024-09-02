import streamlit as st
from src import config
from src.utils import transcribe_audio, process_audio_input, process_text_file
from streamlit_mic_recorder import mic_recorder
import tempfile

def render_input_step():
    st.header("Stap 2: Invoer")
    
    if 'transcription_complete' not in st.session_state:
        st.session_state.transcription_complete = False
    if 'is_recording' not in st.session_state:
        st.session_state.is_recording = False
    if 'input_text' not in st.session_state:
        st.session_state.input_text = ""
    if 'audio_data' not in st.session_state:
        st.session_state.audio_data = None

    if not st.session_state.is_recording:
        input_method = st.radio(
            "Kies invoermethode:",
            ["Audio uploaden", "Audio opnemen", "Tekst schrijven/plakken", "Tekstbestand uploaden"],
            key="input_method_radio"
        )

        if input_method == "Audio uploaden" and not st.session_state.transcription_complete:
            uploaded_file = st.file_uploader("Upload een audiobestand", type=config.ALLOWED_AUDIO_TYPES, key="audio_uploader")
            if uploaded_file:
                st.session_state.uploaded_audio = uploaded_file
                if st.button("Verwerk audio", key="process_audio_button"):
                    process_uploaded_audio(uploaded_file)

        elif input_method == "Audio opnemen" and not st.session_state.transcription_complete:
            st.write("Klik op de knop om de opname te starten.")
            audio_data = mic_recorder(key="audio_recorder", start_prompt="Start opname", stop_prompt="Stop opname", use_container_width=True)
            
            if audio_data is not None:
                if isinstance(audio_data, dict) and audio_data.get("state") == "recording":
                    st.session_state.is_recording = True
                    st.rerun()
                elif isinstance(audio_data, dict) and 'bytes' in audio_data:
                    st.session_state.audio_data = audio_data
                    process_recorded_audio(audio_data)

        elif input_method == "Tekst schrijven/plakken" and not st.session_state.transcription_complete:
            st.session_state.input_text = st.text_area("Voer tekst in of plak tekst:", height=300, key="text_input_area")
            if st.button("Verwerk tekst", key="process_text_button"):
                if st.session_state.input_text:
                    st.session_state.transcription_complete = True
                    st.success("Tekst succesvol verwerkt!")
                else:
                    st.warning("Voer eerst tekst in voordat u op 'Verwerk tekst' klikt.")

        elif input_method == "Tekstbestand uploaden" and not st.session_state.transcription_complete:
            uploaded_file = st.file_uploader("Upload een tekstbestand", type=config.ALLOWED_TEXT_TYPES, key="text_file_uploader")
            if uploaded_file:
                st.session_state.uploaded_text = uploaded_file
                if st.button("Verwerk bestand", key="process_file_button"):
                    process_uploaded_text(uploaded_file)

    else:  # This block will only show when recording is in progress
        st.write("Opname is bezig. Klik op 'Stop opname' om de opname te beëindigen.")
        audio_data = mic_recorder(key="audio_recorder_in_progress", start_prompt="Start opname", stop_prompt="Stop opname", use_container_width=True)
        
        if audio_data is not None and isinstance(audio_data, dict) and 'bytes' in audio_data:
            st.session_state.is_recording = False
            st.session_state.audio_data = audio_data
            process_recorded_audio(audio_data)
            st.rerun()

    if st.session_state.transcription_complete:
        st.markdown("### Transcript")
        st.session_state.input_text = st.text_area("Bewerk indien nodig:", value=st.session_state.input_text, height=300, key="final_transcript")

    # Navigation buttons
    col1, col2, col3 = st.columns([1, 1, 1])
    with col1:
        if st.button("Vorige", key="previous_button"):
            if st.session_state.is_recording:
                st.warning("Stop eerst de opname voordat u teruggaat.")
            else:
                st.session_state.step -= 1
                st.rerun()
    
    with col3:
        if st.button("Volgende", key="next_button"):
            if st.session_state.is_recording:
                st.warning("Stop eerst de opname voordat u verdergaat.")
            elif st.session_state.transcription_complete:
                st.session_state.step += 1
                st.rerun()
            else:
                st.warning("Verwerk eerst de invoer voordat u doorgaat.")
    
def process_uploaded_audio(uploaded_file):
    st.info("Audiobestand geüpload. Transcriptie wordt gestart...")
    with st.spinner("Audio wordt verwerkt en getranscribeerd..."):
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp_file:
            tmp_file.write(uploaded_file.getvalue())
            tmp_file_path = tmp_file.name
        st.session_state.input_text = transcribe_audio(tmp_file_path)
        if st.session_state.input_text:
            st.success("Audio succesvol verwerkt en getranscribeerd!")
            st.write("Transcript lengte:", len(st.session_state.input_text))
            st.write("Eerste 100 karakters van transcript:", st.session_state.input_text[:100])
            st.session_state.transcription_complete = True
        else:
            st.error("Transcriptie is mislukt. Probeer een ander audiobestand.")

def process_recorded_audio(audio_data):
    with st.spinner("Audio wordt verwerkt en getranscribeerd..."):
        audio_file_path = process_audio_input(audio_data)
        if audio_file_path:
            st.session_state.input_text = transcribe_audio(audio_file_path)
            if st.session_state.input_text:
                st.success("Audio succesvol opgenomen en getranscribeerd!")
                st.write("Transcript lengte:", len(st.session_state.input_text))
                st.write("Eerste 100 karakters van transcript:", st.session_state.input_text[:100])
                st.session_state.transcription_complete = True
            else:
                st.error("Transcriptie is mislukt. Probeer opnieuw op te nemen.")

def process_uploaded_text(uploaded_file):
    st.info("Bestand geüpload. Verwerking wordt gestart...")
    with st.spinner("Bestand wordt verwerkt..."):
        st.session_state.input_text = process_text_file(uploaded_file)
        if st.session_state.input_text:
            st.session_state.transcription_complete = True
            st.success("Bestand succesvol geüpload en verwerkt!")
            st.write("Transcript lengte:", len(st.session_state.input_text))
            st.write("Eerste 100 karakters van transcript:", st.session_state.input_text[:100])
        else:
            st.error("Verwerking is mislukt. Probeer een ander bestand.")