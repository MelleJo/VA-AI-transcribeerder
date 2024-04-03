import streamlit as st
from openai import OpenAI
from streamlit_mic_recorder import mic_recorder
import tempfile
import os
import openai

openai.api_key = st.secrets["OPENAI_API_KEY"]

def transcribe_audio(file_path):
    try:
        transcript = openai.Audio.transcribe(file=open(file_path), model="whisper-1")
        transcript_text = transcript["data"]["text"]
        return transcript_text
    except Exception as e:
        st.error(f"Transcription failed: {str(e)}")
        return "Transcription failed."

def summarize_text(text, department):
    prompt = f"Summarize the following text for the {department} department:\n\n{text}"
    response = openai.Completion.create(
        model="text-davinci-003",
        prompt=prompt,
        temperature=0.5,
        max_tokens=100,
    )
    return response.choices[0].text.strip()

st.title("Insurance Dossier Summarizer")

department = st.selectbox("Select Your Department", ["Insurance", "Financial Advice", "Claims", "Customer Service"])

input_method = st.radio("Choose input method:", ["Upload Text", "Upload Audio", "Paste Text", "Type Directly", "Record Audio"])

if input_method == "Upload Text":
    uploaded_file = st.file_uploader("Choose a file")
    if uploaded_file is not None:
        text = uploaded_file.getvalue().decode("utf-8")
        summary = summarize_text(text, department)
        st.text_area("Summary", value=summary, height=250)

elif input_method in ["Upload Audio", "Record Audio"]:
    if input_method == "Upload Audio":
        uploaded_audio = st.file_uploader("Upload an audio file", type=['wav', 'mp3', 'mp4', 'm4a', 'ogg', 'webm'])
    else:
        audio_data = mic_recorder(
            key="recorder",
            start_prompt="Start recording",
            stop_prompt="Stop recording",
            use_container_width=True,
            format="webm"
        )
        uploaded_audio = None if not audio_data or 'bytes' not in audio_data else audio_data['bytes']

    if uploaded_audio is not None:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".webm" if input_method == "Record Audio" else None) as tmp_audio:
            tmp_audio.write(uploaded_audio if input_method == "Record Audio" else uploaded_audio.getvalue())
            transcript = transcribe_audio(tmp_audio.name)
            summary = summarize_text(transcript, department)
            st.text_area("Transcript", value=transcript, height=250)
            st.text_area("Summary", value=summary, height=250)
            os.remove(tmp_audio.name)

elif input_method == "Paste Text":
    text = st.text_area("Paste text here:")
    if st.button("Summarize"):
        summary = summarize_text(text, department)
        st.text_area("Summary", value=summary, height=250)

elif input_method == "Type Directly":
    text = st.text_area("Type text here:")
    if st.button("Summarize"):
        summary = summarize_text(text, department)
        st.text_area("Summary", value=summary, height=250)
