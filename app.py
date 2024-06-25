import streamlit as st
from openai import OpenAI
from streamlit_mic_recorder import mic_recorder
import os
import tempfile
from datetime import datetime
from PyPDF2 import PdfReader
from docx import Document
from pydub import AudioSegment
import pytz
import pyperclip
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
import streamlit.components.v1 as components
import pandas as pd
import html

PROMPTS_DIR = os.path.abspath("prompts")
QUESTIONS_DIR = os.path.abspath("questions")

client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

# Initialize session state variables
if 'gesprekslog' not in st.session_state:
    st.session_state['gesprekslog'] = []
if 'transcript' not in st.session_state:
    st.session_state['transcript'] = ""
if 'summary' not in st.session_state:
    st.session_state['summary'] = ""
if 'input_text' not in st.session_state:
    st.session_state['input_text'] = ""
if 'department' not in st.session_state:
    st.session_state['department'] = "Bedrijven"
if 'input_method' not in st.session_state:
    st.session_state['input_method'] = "Voer tekst in of plak tekst"
if 'processing_audio' not in st.session_state:
    st.session_state['processing_audio'] = False

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
            "test-prompt (alleen voor Melle!)": "util/test_prompt.txt"
        }
        prompt_file = department_prompts.get(department, f"{department.lower().replace(' ', '_')}_prompt.txt")
        department_prompt = load_prompt(prompt_file)
        basic_prompt = load_prompt("util/basic_prompt.txt")
        current_time = get_local_time()
        combined_prompt = f"{department_prompt}\n\n{basic_prompt.format(current_time=current_time)}\n\n{text}"
        chat_model = ChatOpenAI(api_key=st.secrets["OPENAI_API_KEY"], model="gpt-4", temperature=0)
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
    text_to_copy = f"Transcript:\n\n{transcript}\n\nSummary:\n\n{summary}"
    pyperclip.copy(text_to_copy)
    st.success("Transcript and summary copied to clipboard!")

def main():
    st.set_page_config(page_title="Gesprekssamenvatter", page_icon="🎙️", layout="wide")
    
    st.title("Gesprekssamenvatter - testversie 0.3.0")

    st.markdown("""
    <style>
    .summary-box {
        border: 2px solid #3498db;
        border-radius: 10px;
        padding: 20px;
        margin: 20px 0;
        background-color: #f0f8ff;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    }
    .summary-box h3 {
        color: #2c3e50;
        border-bottom: 2px solid #3498db;
        padding-bottom: 10px;
        margin-bottom: 20px;
        text-align: center;
    }
    .content {
        white-space: pre-wrap;
        word-wrap: break-word;
        font-size: 16px;
        line-height: 1.6;
    }
    .transcript-box {
        border: 1px solid #ddd;
        border-radius: 5px;
        padding: 10px;
        margin-bottom: 20px;
        background-color: #f9f9f9;
    }
    .copy-button {
        text-align: center;
        margin-top: 20px;
    }
    </style>
    """, unsafe_allow_html=True)

    col1, col2 = st.columns([1, 3])

    with col1:
        st.session_state['department'] = st.selectbox("Kies je afdeling", 
            ["Bedrijven", "Financieel Advies", "Schadeafdeling", "Algemeen", "Arbo", "Algemene samenvatting", 
             "Ondersteuning Bedrijfsarts", "Onderhoudsadviesgesprek in tabelvorm", "Notulen van een vergadering", 
             "Verslag van een telefoongesprek", "Deelnemersgesprekken collectief pensioen", "test-prompt (alleen voor Melle!)"],
            key='department_select')
        
        if st.session_state['department'] in ["Bedrijven", "Financieel Advies", "Schadeafdeling", "Algemeen", "Arbo", "Algemene samenvatting", "Ondersteuning Bedrijfsarts", "Onderhoudsadviesgesprek in tabelvorm", "Notulen van een vergadering", "Verslag van een telefoongesprek", "Deelnemersgesprekken collectief pensioen", "test-prompt (alleen voor Melle!)"]:
            with st.expander("Vragen om te overwegen"):
                questions = load_questions(f"{st.session_state['department'].lower().replace(' ', '_')}.txt")
                for question in questions:
                    st.markdown(f"- {question.strip()}")

        st.session_state['input_method'] = st.radio("Wat wil je laten samenvatten?", 
                                                    ["Voer tekst in of plak tekst", "Upload tekst", "Upload audio", "Neem audio op"],
                                                    key='input_method_radio')

    with col2:
        if st.session_state['input_method'] == "Upload tekst":
            uploaded_file = st.file_uploader("Choose a file", type=['txt', 'docx', 'pdf'])
            if uploaded_file is not None:
                if uploaded_file.name.endswith('.docx'):
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".docx") as tmp_docx:
                        tmp_docx.write(uploaded_file.getvalue())
                        tmp_docx_path = tmp_docx.name
                    st.session_state['transcript'] = read_docx(tmp_docx_path)
                    os.remove(tmp_docx_path)
                elif uploaded_file.name.endswith('.pdf'):
                    pdf_reader = PdfReader(uploaded_file)
                    st.session_state['transcript'] = ""
                    for page in pdf_reader.pages:
                        st.session_state['transcript'] += page.extract_text()
                else:
                    st.session_state['transcript'] = uploaded_file.getvalue().decode("utf-8")
                
                st.session_state['summary'] = summarize_text(st.session_state['transcript'], st.session_state['department'])
                update_gesprekslog(st.session_state['transcript'], st.session_state['summary'])

        elif st.session_state['input_method'] == "Voer tekst in of plak tekst":
            st.session_state['input_text'] = st.text_area("Voeg tekst hier in:", 
                                                          value=st.session_state['input_text'], 
                                                          height=300,
                                                          key='input_text_area')
            if st.button("Samenvatten"):
                if st.session_state['input_text']:
                    st.session_state['transcript'] = st.session_state['input_text']
                    st.session_state['summary'] = summarize_text(st.session_state['transcript'], st.session_state['department'])
                    update_gesprekslog(st.session_state['transcript'], st.session_state['summary'])
                else:
                    st.warning("Voer alstublieft wat tekst in om te samenvatten.")

        elif st.session_state['input_method'] == "Upload audio":
            uploaded_file = st.file_uploader("Upload an audio file", type=['wav', 'mp3', 'mp4', 'm4a', 'ogg', 'webm'])
            if uploaded_file is not None and not st.session_state['processing_audio']:
                st.session_state['processing_audio'] = True
                with st.spinner("Verwerken van audio..."):
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp_audio:
                        tmp_audio.write(uploaded_file.getvalue())
                        tmp_audio.flush()
                    st.session_state['transcript'] = transcribe_audio(tmp_audio.name)
                    os.remove(tmp_audio.name)
                    st.session_state['summary']
                    st.session_state['summary'] = summarize_text(st.session_state['transcript'], st.session_state['department'])
                    update_gesprekslog(st.session_state['transcript'], st.session_state['summary'])
                st.session_state['processing_audio'] = False
                st.experimental_rerun()

        elif st.session_state['input_method'] == "Neem audio op":
            audio_data = mic_recorder(key="recorder", start_prompt="Start opname", stop_prompt="Stop opname", use_container_width=True, format="webm")
            if audio_data and 'bytes' in audio_data and not st.session_state['processing_audio']:
                st.session_state['processing_audio'] = True
                with st.spinner("Verwerken van audio..."):
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp_audio:
                        tmp_audio.write(audio_data['bytes'])
                        tmp_audio.flush()
                    st.session_state['transcript'] = transcribe_audio(tmp_audio.name)
                    os.remove(tmp_audio.name)
                    st.session_state['summary'] = summarize_text(st.session_state['transcript'], st.session_state['department'])
                    update_gesprekslog(st.session_state['transcript'], st.session_state['summary'])
                st.session_state['processing_audio'] = False
                st.experimental_rerun()

        # Display transcript and summary
        if st.session_state['transcript']:
            with st.expander("Toon Transcript", expanded=False):
                st.markdown('<div class="transcript-box">', unsafe_allow_html=True)
                st.markdown('<h4>Transcript</h4>', unsafe_allow_html=True)
                st.markdown(f'<div class="content">{html.escape(st.session_state["transcript"])}</div>', unsafe_allow_html=True)
                st.markdown('</div>', unsafe_allow_html=True)
        
        if st.session_state['summary']:
            st.markdown('<div class="summary-box">', unsafe_allow_html=True)
            st.markdown('<h3>Samenvatting</h3>', unsafe_allow_html=True)
            st.markdown(st.session_state['summary'], unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)

            if st.button("Kopieer naar klembord"):
                copy_to_clipboard(st.session_state['transcript'], st.session_state['summary'])

    # Display conversation history
    with st.expander("Laatste vijf gesprekken"):
        for i, gesprek in enumerate(st.session_state['gesprekslog']):
            st.markdown(f"**Gesprek {i+1} op {gesprek['time']}**")
            with st.expander("Toon Transcript"):
                st.markdown(f'<div class="content">{html.escape(gesprek["transcript"])}</div>', unsafe_allow_html=True)
            with st.expander("Toon Samenvatting"):
                st.markdown(gesprek["summary"], unsafe_allow_html=True)
            st.markdown("---")

if __name__ == "__main__":
    main()