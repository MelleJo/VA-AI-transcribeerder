import streamlit as st
from pydub import AudioSegment
import tempfile
import os
from streamlit_mic_recorder import mic_recorder
from services.summarization_service import run_summarization
from utils.text_processing import update_gesprekslog
from openai import OpenAI
import logging

logger = logging.getLogger(__name__)

# Initialize the OpenAI client
try:
    client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
except Exception as e:
    logger.error(f"Error initializing OpenAI client: {str(e)}")
    st.error("There was an error initializing the OpenAI client. Please check your API key.")

SUPPORTED_FORMATS = ['flac', 'm4a', 'mp3', 'mp4', 'mpeg', 'mpga', 'oga', 'ogg', 'wav', 'webm']

def process_audio_input(input_method):
    if input_method == "Upload audio":
        uploaded_file = st.file_uploader("Upload an audio file", type=SUPPORTED_FORMATS)
        if uploaded_file is not None:
            with st.spinner("Transcriberen van audio..."):
                try:
                    with tempfile.NamedTemporaryFile(delete=False, suffix=f".{uploaded_file.name.split('.')[-1]}") as tmp_audio:
                        tmp_audio.write(uploaded_file.getvalue())
                        tmp_audio.flush()
                        
                    # Convert to MP3 if not already
                    mp3_path = convert_to_mp3(tmp_audio.name)
                    
                    transcript = transcribe_audio(mp3_path)
                    st.session_state.transcript = transcript
                    st.info(f"Transcript gegenereerd. Lengte: {len(transcript)}")
                except Exception as e:
                    st.error(f"Error transcribing audio: {str(e)}")
                    logger.error(f"Error transcribing audio: {str(e)}")
                finally:
                    # Clean up temporary files
                    if 'tmp_audio' in locals():
                        os.unlink(tmp_audio.name)
                    if 'mp3_path' in locals():
                        os.unlink(mp3_path)
    elif input_method == "Neem audio op":
        audio_data = mic_recorder(key="recorder", start_prompt="Start opname", stop_prompt="Stop opname", use_container_width=True)
        if audio_data and 'bytes' in audio_data:
            with st.spinner("Transcriberen van audio..."):
                try:
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".webm") as tmp_audio:
                        tmp_audio.write(audio_data['bytes'])
                        tmp_audio.flush()
                    
                    # Convert to MP3
                    mp3_path = convert_to_mp3(tmp_audio.name)
                    
                    transcript = transcribe_audio(mp3_path)
                    st.session_state.transcript = transcript
                    st.info(f"Transcript gegenereerd. Lengte: {len(transcript)}")
                except Exception as e:
                    st.error(f"Error transcribing audio: {str(e)}")
                    logger.error(f"Error transcribing audio: {str(e)}")
                finally:
                    # Clean up temporary files
                    if 'tmp_audio' in locals():
                        os.unlink(tmp_audio.name)
                    if 'mp3_path' in locals():
                        os.unlink(mp3_path)

    if st.session_state.transcript:
        with st.spinner("Genereren van samenvatting..."):
            result = run_summarization(st.session_state.transcript, st.session_state.prompt, st.session_state.user_name)
            if result["error"] is None:
                st.session_state.summary = result["summary"]
                update_gesprekslog(st.session_state.transcript, result["summary"])
                st.success("Samenvatting voltooid!")
            else:
                st.error(f"Er is een fout opgetreden bij het genereren van de samenvatting: {result['error']}")

def convert_to_mp3(file_path):
    audio = AudioSegment.from_file(file_path)
    mp3_path = file_path.rsplit('.', 1)[0] + '.mp3'
    audio.export(mp3_path, format="mp3")
    return mp3_path

def transcribe_audio(file_path):
    if not client:
        raise Exception("OpenAI client is not initialized. Please check your API key.")
    
    try:
        with open(file_path, "rb") as audio_file:
            transcript = client.audio.transcriptions.create(
                file=audio_file,
                model="whisper-1",
                response_format="text"
            )
        return transcript
    except Exception as e:
        logger.error(f"Error in transcribe_audio: {str(e)}")
        raise Exception(f"Error transcribing audio: {str(e)}")

def split_audio(file_path, max_duration_ms=30000):
    audio = AudioSegment.from_file(file_path)
    chunks = []
    for i in range(0, len(audio), max_duration_ms):
        chunks.append(audio[i:i+max_duration_ms])
    return chunks