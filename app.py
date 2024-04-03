import streamlit as st
from openai import OpenAI
from streamlit_mic_recorder import mic_recorder
import os
import time
import tempfile
from PyPDF2 import PdfReader
from langchain.text_splitter import CharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain.chains import AnalyzeDocumentChain
from langchain_community.callbacks import get_openai_callback
from langchain.chains.question_answering import load_qa_chain
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from fuzzywuzzy import process

client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

def transcribe_audio(file_path):
    try:
        with open(file_path, "rb") as audio_file:
            transcription_response = client.audio.transcriptions.create(file=audio_file, model="whisper-1")
            transcript_text = transcription_response.text if hasattr(transcription_response, 'text') else "Transcription text not found."
            return transcript_text
    except Exception as e:
        st.error(f"Transcription failed: {str(e)}")
        return "Transcription failed."


opdracht = "Maak een samenvatting op basis van de prompts en de gegeven tekst"


def summarize_text(text, department):
    # Department-specific prompts setup
    department_prompts = {
        "Verzekeringen": "Je bent expert in het samenvatten van gesprekken over verzekeringen.",
        "Financieel Advies": "Je bent een expert in het samenvatten van gesprekken over financieel advies.",
        "Claims": "Je bent een expert in het samenvatten van gesprekken over claims.",
        "Klantenservice": "Je bent een expert in het samenvatten van gesprekken over allerlei soort vragen van klanten."
    }

    basic_prompt = "Hier is de input, dit ga je samenvatten."

    chat = ChatOpenAI(api_key=st.secrets["OPENAI_API_KEY"], temperature=0.5)

    messages = [
        SystemMessage(content=department_prompts.get(department, "") + "\n" + basic_prompt),
        HumanMessage(content=text)
    ]

    # Invoke the chat model and obtain the summary
    response = chat.invoke(messages)
    summary_text = response.content if response else "Unable to generate summary."

    return summary_text

st.title("Gesprekssamenvatter")

department = st.selectbox("Kies je afdeling", ["Verzekeringen", "Financieel Advies", "Claims", "Klantenservice"])

input_method = st.radio("Wat wil je laten samenvatten?", ["Upload tekst", "Upload Audio", "Voer tekst in of plak tekst", "Neem audio op"])

if input_method == "Upload tekst":
    uploaded_file = st.file_uploader("Choose a file")
    if uploaded_file is not None:
        text = uploaded_file.getvalue().decode("utf-8")
        summary = summarize_text(text, department)
        st.text_area("Summary", value=summary, height=250)

elif input_method in ["Upload Audio", "Neem audio op"]:
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

elif input_method == "Enter or Paste Text":
    text = st.text_area("Enter or paste the text here:")
    if st.button("Summarize"):
        summary = summarize_text(text, department)
        st.text_area("Summary", value=summary, height=250)
