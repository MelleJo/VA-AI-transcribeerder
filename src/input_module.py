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

    input_method = st.radio("Kies invoermethode:", 
                            ["Audio uploaden", "Audio opnemen", "Tekst schrijven/plakken", "Tekstbestand uploaden"],
                            disabled=st.session_state.is_recording)
    
    if input_method == "Audio uploaden" and not st.session_state.transcription_complete:
        uploaded_file = st.file_uploader("Upload een audiobestand", type=config.ALLOWED_AUDIO_TYPES, disabled=st.session_state.is_recording)
        if uploaded_file is not None:
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

    elif input_method == "Audio opnemen" and not st.session_state.transcription_complete:
        st.write("Klik op de knop om de opname te starten.")
        audio_data = mic_recorder(key="recorder", start_prompt="Start opname", stop_prompt="Stop opname", use_container_width=True)
        
        if audio_data is not None:
            if isinstance(audio_data, dict) and audio_data.get("state") == "recording":
                st.session_state.is_recording = True
            elif isinstance(audio_data, dict) and 'bytes' in audio_data:
                st.session_state.is_recording = False
                process_recorded_audio(audio_data)

    elif input_method == "Tekst schrijven/plakken" and not st.session_state.transcription_complete:
        st.session_state.input_text = st.text_area("Voer tekst in of plak tekst:", height=300, disabled=st.session_state.is_recording)
        if st.button("Verwerk tekst", disabled=st.session_state.is_recording):
            if st.session_state.input_text:
                st.session_state.transcription_complete = True
                st.success("Tekst succesvol verwerkt!")
                st.write("Transcript lengte:", len(st.session_state.input_text))
                st.write("Eerste 100 karakters van transcript:", st.session_state.input_text[:100])
            else:
                st.warning("Voer eerst tekst in voordat u op 'Verwerk tekst' klikt.")

    elif input_method == "Tekstbestand uploaden" and not st.session_state.transcription_complete:
        uploaded_file = st.file_uploader("Upload een tekstbestand", type=config.ALLOWED_TEXT_TYPES, disabled=st.session_state.is_recording)
        if uploaded_file is not None:
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

    if st.session_state.transcription_complete:
        st.markdown("### Transcript")
        st.session_state.input_text = st.text_area("Bewerk indien nodig:", value=st.session_state.input_text, height=300)

    if st.button("Ga naar Transcript Bewerken", disabled=st.session_state.is_recording):
        if st.session_state.input_text:
            st.session_state.step = 3
            st.rerun()
        else:
            st.warning("Voer eerst tekst in of neem audio op voordat u doorgaat.")

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