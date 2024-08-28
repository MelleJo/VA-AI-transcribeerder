import streamlit as st
from pydub import AudioSegment
import tempfile
from streamlit_mic_recorder import mic_recorder
from services.summarization_service import summarize_text
from utils.text_processing import update_gesprekslog
from openai import OpenAI
import logging

logger = logging.getLogger(__name__)

client = OpenAI()
OpenAI.api_key = st.secrets["OPENAI_API_KEY"]

def process_audio_input(input_method):
    if input_method == "Upload audio":
        uploaded_file = st.file_uploader("Upload an audio file", type=['wav', 'mp3', 'mp4', 'm4a', 'ogg', 'webm'])
        if uploaded_file is not None:
            with st.spinner("Transcriberen van audio..."):
                with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp_audio:
                    tmp_audio.write(uploaded_file.getvalue())
                    tmp_audio.flush()
                transcript = transcribe_audio(tmp_audio.name)
                st.session_state.transcript = transcript
                st.info(f"Transcript gegenereerd. Lengte: {len(transcript)}")
                tempfile.NamedTemporaryFile(delete=True)
    elif input_method == "Neem audio op":
        audio_data = mic_recorder(key="recorder", start_prompt="Start opname", stop_prompt="Stop opname", use_container_width=True)
        if audio_data and 'bytes' in audio_data:
            with st.spinner("Transcriberen van audio..."):
                with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp_audio:
                    tmp_audio.write(audio_data['bytes'])
                    tmp_audio.flush()
                transcript = transcribe_audio(tmp_audio.name)
                st.session_state.transcript = transcript
                st.info(f"Transcript gegenereerd. Lengte: {len(transcript)}")
                tempfile.NamedTemporaryFile(delete=True)

    if st.session_state.transcript:
        with st.spinner("Genereren van samenvatting..."):
            result = summarize_text(st.session_state.transcript, st.session_state.prompt)
            if result:
                st.session_state.summary = result
                update_gesprekslog(st.session_state.transcript, result)
                st.success("Samenvatting voltooid!")
            else:
                st.error("Er is een fout opgetreden bij het genereren van de samenvatting.")

def transcribe_audio(file_path):
    with open(file_path, "rb") as audio_file:
        transcript = client.audio.transcriptions.create(
            file=audio_file,
            model="whisper-1",
            response_format="text"
        )
    return transcript

def split_audio(file_path, max_duration_ms=30000):
    audio = AudioSegment.from_file(file_path)
    chunks = []
    for i in range(0, len(audio), max_duration_ms):
        chunks.append(audio[i:i+max_duration_ms])
    return chunks