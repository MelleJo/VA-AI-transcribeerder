import streamlit as st
import whisper

def process_audio_input(input_method, prompt_path, user_name):
    if input_method == "Neem audio op":
        audio_bytes = st.session_state.get('recorded_audio')
    elif input_method == "Upload audio":
        audio_bytes = st.session_state.get('uploaded_audio')
    else:
        raise ValueError("Invalid input method for audio processing")

    if audio_bytes:
        transcript = transcribe_audio(audio_bytes)
        return {"transcript": transcript, "error": None}
    else:
        return {"transcript": None, "error": "No audio data received"}

def transcribe_audio(audio_bytes):
    model = whisper.load_model("base")
    result = model.transcribe(audio_bytes)
    return result["text"]