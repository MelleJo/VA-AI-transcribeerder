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
        transcript = client.audio.transcriptions.create(file=open(file_path), model="whisper-1")
        transcript_text = transcript["data"]["text"]
        return transcript_text
    except Exception as e:
        st.error(f"Transcriptie mislukt: {str(e)}")
        return "Transcriptie mislukt."

opdracht = "Maak een samenvatting op basis van de prompts en de gegeven tekst"


def transcribe_audio(file_path):
    try:
        # Note: Adjust the path and model as per your specific requirements
        with open(file_path, "rb") as audio_file:
            transcription = openai.Audio.create(
                audio_file=audio_file,
                model="whisper-1",
            )
        transcript_text = transcription['data']['text']
        return transcript_text
    except Exception as e:
        st.error(f"Transcription failed: {str(e)}")
        return "Transcription failed."

def summarize_text(text, department):
    # Department-specific prompts setup
    department_prompts = {
        "Verzekeringen": "You are an insurance expert summarizing policy conditions.",
        "Financieel Advies": "As a financial advisor, summarize the underlying financial principles.",
        "Claims": "As a claims handler, provide a summary focusing on claims and relevant policy conditions.",
        "Klantenservice": "As a customer service representative, summarize the information in an easily understandable way."
    }

    basic_prompt = "Here is a summary of the key points from the text, focusing on the most relevant information for your specific needs."

    chat = ChatOpenAI(api_key=st.secrets["OPENAI_API_KEY"], temperature=0.5)

    messages = [
        SystemMessage(content=department_prompts.get(department, "") + "\n" + basic_prompt),
        HumanMessage(content=text)
    ]

    # Invoke the chat model and obtain the summary
    response = chat.invoke(messages)
    summary_text = response.content if response else "Unable to generate summary."

    return summary_text

st.title("Document Summarizer")

department = st.selectbox("Select your department", ["Verzekeringen", "Financieel Advies", "Claims", "Klantenservice"])

input_method = st.radio("Choose input method:", ["Upload Text", "Upload Audio", "Enter or Paste Text", "Record Audio"])

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

elif input_method == "Enter or Paste Text":
    text = st.text_area("Enter or paste the text here:")
    if st.button("Summarize"):
        summary = summarize_text(text, department)
        st.text_area("Summary", value=summary, height=250)
