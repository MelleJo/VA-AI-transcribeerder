import streamlit as st
from openai import OpenAI
import os
import pytz
import tempfile
from datetime import datetime
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
from docx import Document
from pydub import AudioSegment
import pandas as pd
import pyperclip
from tenacity import *
from tenacity-asyncio import tenacity.asyncio

PROMPTS_DIR = os.path.abspath("prompts")
QUESTIONS_DIR = os.path.abspath("questions")

client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

if 'gesprekslog' not in st.session_state:
    st.session_state['gesprekslog'] = []

def vertaal_dag_eng_naar_nl(dag_engels):
    vertaling = {
        "Monday": "Maandag",
        "Tuesday": "Dinsdag",
        "Wednesday": "Woensdag",
        "Thursday": "Donderdag",
        "Friday": "Vrijdag",
        "Saturday": "Zaterdag",
        "Sunday": "Zondag"
    }
    return vertaling.get(dag_engels, dag_engels)

def split_audio(file_path, max_duration_ms=30000):
    audio = AudioSegment.from_file(file_path)
    chunks = []
    for i in range(0, len(audio), max_duration_ms):
        chunks.append(audio[i:i+max_duration_ms])
    return chunks

def get_local_time():
    timezone = pytz.timezone("Europe/Amsterdam")
    return datetime.now(timezone).strftime('%d-%m-%Y %H:%M:%S')

def transcribe_audio(file_path):
    transcript_text = ""
    with st.spinner('Audio segmentatie wordt gestart...'):
        try:
            audio_segments = split_audio(file_path)
        except Exception as e:
            st.error(f"Fout bij het segmenteren van het audio: {str(e)}")
            return "Segmentatie mislukt."

    total_segments = len(audio_segments)
    progress_bar = st.progress(0)
    progress_text = st.empty()
    progress_text.text("Start transcriptie...")
    for i, segment in enumerate(audio_segments):
        progress_text.text(f'Bezig met verwerken van segment {i+1} van {total_segments} - {((i+1)/total_segments*100):.2f}% voltooid')
        with tempfile.NamedTemporaryFile(delete=True, suffix='.wav') as temp_file:
            segment.export(temp_file.name, format="wav")
            with open(temp_file.name, "rb") as audio_file:
                try:
                    transcription_response = client.audio.transcriptions.create(file=audio_file, model="whisper-1")
                    if hasattr(transcription_response, 'text'):
                        transcript_text += transcription_response.text + " "
                except Exception as e:
                    st.error(f"Fout bij het transcriberen: {str(e)}")
                    continue
        progress_bar.progress((i + 1) / total_segments)
    progress_text.success("Transcriptie voltooid.")
    return transcript_text.strip()

def load_prompt(file_name):
    path = os.path.join(PROMPTS_DIR, file_name)
    if not os.path.exists(path):
        st.error(f"Bestand niet gevonden: {path}")
        raise FileNotFoundError(f"Bestand niet gevonden: {path}")
    with open(path, "r", encoding="utf-8") as file:
        return file.read()

def load_questions(file_name):
    path = os.path.join(QUESTIONS_DIR, file_name)
    if not os.path.exists(path):
        st.error(f"Bestand niet gevonden: {path}")
        raise FileNotFoundError(f"Bestand niet gevonden: {path}")
    with open(path, "r", encoding="utf-8") as file:
        return file.readlines()

def read_docx(file_path):
    doc = Document(file_path)
    fullText = []
    for para in doc.paragraphs:
        fullText.append(para.text)
    return '\n'.join(fullText)

def summarize_text(text, department):
    with st.spinner("Samenvatting maken..."):
        department_prompts = {
            "Bedrijven": "veldhuis-advies-groep/bedrijven/MKB/onderhoudsadviesgesprek_tabel_prompt.txt",
            "Financieel Advies": "veldhuis-advies-groep/bedrijven/MKB/onderhoudsadviesgesprek_tabel_prompt.txt",
            "Schadeafdeling": "veldhuis-advies-groep/bedrijven/MKB/onderhoudsadviesgesprek_tabel_prompt.txt",
            "Algemeen": "algemeen/notulen/algemeen_notulen.txt",
            "Arbo": "arbo/algemeen_arbo.txt",
            "Ondersteuning Bedrijfsarts": "arbo/ondersteuning_bedrijfsarts/samenvatting_gesprek_bedrijfsarts.txt",
            "Onderhoudsadviesgesprek in tabelvorm": "veldhuis-advies-groep/bedrijven/MKB/onderhoudsadviesgesprek_tabel_prompt.txt",
            "Notulen van een vergadering": "algemeen/notulen/algemeen_notulen.txt",
            "Verslag van een telefoongesprek": "algemeen/telefoon/algemeen_telefoon.txt",
            "test-prompt (alleen voor Melle!)": "util/test_prompt.txt",
            "Deelnemersgesprekken collectief pensioen": "veldhuis-advies/collectief/deelnemersgesprek.txt"
        }
        prompt_file = department_prompts.get(department, f"{department.lower().replace(' ', '_')}_prompt.txt")
        department_prompt = load_prompt(prompt_file)
        basic_prompt = load_prompt("util/basic_prompt.txt")
        current_time = get_local_time()
        combined_prompt = f"{department_prompt}\n\n{basic_prompt.format(current_time=current_time)}\n\n{text}"
        chat_model = ChatOpenAI(api_key=st.secrets["OPENAI_API_KEY"], model="gpt-4o", temperature=0)
        prompt_template = ChatPromptTemplate.from_template(combined_prompt)
        llm_chain = prompt_template | chat_model | StrOutputParser()
        try:
            summary_text = llm_chain.invoke({"text": text})
            if not summary_text:
                summary_text = "Mislukt om een samenvatting te genereren."
        except Exception as e:
            st.error(f"Fout bij het genereren van samenvatting: {e}")
            summary_text = "Mislukt om een samenvatting te genereren."
        return summary_text

def update_gesprekslog(transcript, summary):
    current_time = get_local_time()
    st.session_state['gesprekslog'].insert(0, {'time': current_time, 'transcript': transcript, 'summary': summary})
    st.session_state['gesprekslog'] = st.session_state['gesprekslog'][:5]

def copy_to_clipboard(transcript, summary):
    text_to_copy = f"""
    <html>
    <head>
        <style>
            body {{
                font-family: Arial, sans-serif;
                font-size: 10pt;
            }}
            h1 {{
                font-weight: bold;
            }}
        </style>
    </head>
    <body>
        <h1>Transcript</h1>
        <p>{transcript}</p>
        <h1>Summary</h1>
        <p>{summary}</p>
    </body>
    </html>
    """
    pyperclip.copy(text_to_copy)
    st.success("Transcript and summary copied to clipboard!")

def main():
    st.title("Gesprekssamenvatter - testversie 0.1.8.")

    with st.sidebar:
        st.header("Settings")
        department = st.selectbox("Kies je afdeling", ["Bedrijven", "Financieel Advies", "Schadeafdeling", "Algemeen", "Arbo", "Algemene samenvatting", "Ondersteuning Bedrijfsarts", "Onderhoudsadviesgesprek in tabelvorm", "Notulen van een vergadering", "Verslag van een telefoongesprek", "Deelnemersgesprekken collectief pensioen", "test-prompt (alleen voor Melle!)"])
        if department in ["Bedrijven", "Financieel Advies", "Schadeafdeling", "Algemeen", "Arbo", "Algemene samenvatting", "Ondersteuning Bedrijfsarts", "Onderhoudsadviesgesprek in tabelvorm", "Notulen van een vergadering", "Verslag van een telefoongesprek", "Deelnemersgesprekken collectief pensioen", "test-prompt (alleen voor Melle!)"]:
            st.subheader("Vragen/onderwerpen om in je input te overwegen:")
            questions = load_questions(f"{department.lower().replace(' ', '_')}.txt")
            for question in questions:
                st.markdown(f'<p>- {question.strip()}</p>', unsafe_allow_html=True)

        # Add the text input and summarize button
        text_input = st.text_area("Voeg tekst hier in:")
        summarize_button = st.button("Samenvatten")

    if summarize_button and text_input:
        transcript = text_input  # Assuming transcript is the input text for now
        summary = summarize_text(text_input, department)
        update_gesprekslog(transcript, summary)

        # Display the latest transcript and summary
        st.markdown(f"<h1>Transcript</h1><p>{transcript}</p>", unsafe_allow_html=True)
        st.markdown(f"<h1>Summary</h1><p>{summary}</p>", unsafe_allow_html=True)

        # Add the button to copy to clipboard
        if st.button("Copy Transcript and Summary to Clipboard"):
            copy_to_clipboard(transcript, summary)

if __name__ == "__main__":
    main()
