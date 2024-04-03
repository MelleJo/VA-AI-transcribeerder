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
        st.error(f"Transcriptie mislukt: {str(e)}")
        return "Transcriptie mislukt."

def summarize_text(text, department):
    prompt = f"Vat de volgende tekst samen voor de afdeling {department}:\n\n{text}"
    response = openai.Completion.create(
        model="text-davinci-003",
        prompt=prompt,
        temperature=0.5,
        max_tokens=100,
    )
    return response.choices[0].text.strip()

st.title("Dossier Samenvatter")

department = st.selectbox("Selecteer uw afdeling", ["Verzekeringen", "Financieel Advies", "Claims", "Klantenservice"])

input_method = st.radio("Kies invoermethode:", ["Tekst uploaden", "Audio uploaden", "Tekst invoeren of plakken", "Audio opnemen"])

if input_method == "Tekst uploaden":
    uploaded_file = st.file_uploader("Kies een bestand")
    if uploaded_file is not None:
        text = uploaded_file.getvalue().decode("utf-8")
        summary = summarize_text(text, department)
        st.text_area("Samenvatting", value=summary, height=250)

elif input_method == "Audio uploaden" or input_method == "Audio opnemen":
    if input_method == "Audio uploaden":
        uploaded_audio = st.file_uploader("Upload een audiobestand", type=['wav', 'mp3', 'mp4', 'm4a', 'ogg', 'webm'])
    else:
        audio_data = mic_recorder(
            key="recorder",
            start_prompt="Begin met opnemen",
            stop_prompt="Stop opname",
            use_container_width=True,
            format="webm"
        )
        uploaded_audio = None if not audio_data or 'bytes' not in audio_data else audio_data['bytes']

    if uploaded_audio is not None:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".webm" if input_method == "Audio opnemen" else None) as tmp_audio:
            tmp_audio.write(uploaded_audio if input_method == "Audio opnemen" else uploaded_audio.getvalue())
            transcript = transcribe_audio(tmp_audio.name)
            summary = summarize_text(transcript, department)
            st.text_area("Transcript", value=transcript, height=250)
            st.text_area("Samenvatting", value=summary, height=250)
            os.remove(tmp_audio.name)

elif input_method == "Tekst invoeren of plakken":
    text = st.text_area("Voer of plak de tekst hier:")
    if st.button("Samenvatten"):
        summary = summarize_text(text, department)
        st.text_area("Samenvatting", value=summary, height=250)
