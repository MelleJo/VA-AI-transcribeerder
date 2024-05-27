import streamlit as st
from openai import OpenAI
from streamlit_mic_recorder import mic_recorder
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
import streamlit.components.v1 as components
import pandas as pd


BASE_DIR = os.path.join(os.getcwd(), "preloaded_pdfs", "PolisvoorwaardenVA")

PROMPTS_DIR = os.path.join(os.getcwd(), "prompts")
QUESTIONS_DIR = os.path.join(os.getcwd(), "questions")

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

def summarize_ondersteuning_bedrijfsarts(text):
    detailed_prompt = load_prompt("arbo/ondersteuning_bedrijfsarts/samenvatting_gesprek_bedrijfsarts.txt")
    detailed_prompt = detailed_prompt.format(text=text)
    
    chat_model = ChatOpenAI(api_key=st.secrets["OPENAI_API_KEY"], model="gpt-4o", temperature=0)
    prompt_template = ChatPromptTemplate.from_template(detailed_prompt)
    llm_chain = prompt_template | chat_model | StrOutputParser()
    
    try:
        summary = llm_chain.invoke({})
        if not summary:
            summary = "Mislukt om een samenvatting te genereren."
    except Exception as e:
        st.error(f"Fout bij het genereren van samenvatting: {e}")
        summary = "Mislukt om een samenvatting te genereren."
    
    return summary

def summarize_onderhoudsadviesgesprek_tabel(text):
    detailed_prompt = load_prompt("veldhuis-advies-groep/bedrijven/MKB/onderhoudsadviesgesprek_tabel_prompt.txt")
    detailed_prompt = detailed_prompt.format(text=text)
    
    chat_model = ChatOpenAI(api_key=st.secrets["OPENAI_API_KEY"], model="gpt-4o", temperature=0)
    prompt_template = ChatPromptTemplate.from_template(detailed_prompt)
    llm_chain = prompt_template | chat_model | StrOutputParser()
    
    try:
        summary = llm_chain.invoke({})
        if not summary:
            summary = "Mislukt om een samenvatting te genereren."
    except Exception as e:
        st.error(f"Fout bij het genereren van samenvatting: {e}")
        summary = "Mislukt om een samenvatting te genereren."
    
    def parse_table(table_text):
        rows = table_text.split("\n")
        if len(rows) < 2:
            st.error("Het lijkt erop dat de tabel niet correct is gegenereerd.")
            return pd.DataFrame()
        headers = [header.strip() for header in rows[1].split("|")[1:-1]]
        data = [row.split("|")[1:-1] for row in rows[3:] if row]
        return pd.DataFrame(data, columns=headers)
    
    if summary:
        zakelijk_risico_start = summary.find("Zakelijke Risico's:")
        prive_risico_start = summary.find("Privé Risico's:")
        
        zakelijk_risico_table = summary[zakelijk_risico_start:prive_risico_start].strip()
        prive_risico_table = summary[prive_risico_start:].strip()
        
        zakelijk_risico_df = parse_table(zakelijk_risico_table)
        prive_risico_df = parse_table(prive_risico_table)
        
        return summary, zakelijk_risico_df, prive_risico_df
    
    return summary, None, None

def load_prompt(file_name):
    path = os.path.join(PROMPTS_DIR, file_name)
    with open(path, "r", encoding="utf-8") as file:
        return file.read()

def load_questions(file_name):
    path = os.path.join(QUESTIONS_DIR, file_name)
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
        if department == "Onderhoudsadviesgesprek in tabelvorm":
            summary, zakelijk_risico_df, prive_risico_df = summarize_onderhoudsadviesgesprek_tabel(text)
            if summary:
                st.markdown(f"**Samenvatting:**\n{summary}", unsafe_allow_html=True)
                if zakelijk_risico_df is not None and prive_risico_df is not None:
                    st.subheader("Zakelijke Risico's")
                    st.table(zakelijk_risico_df)
                    st.subheader("Privé Risico's")
                    st.table(prive_risico_df)
                return summary
            else:
                st.error("Er is een fout opgetreden bij het genereren van de samenvatting.")
        elif department == "Ondersteuning Bedrijfsarts":
            return summarize_ondersteuning_bedrijfsarts(text)
        else:
            prompt_file = f"veldhuis-advies-groep/bedrijven/MKB/{department.lower().replace(' ', '_')}_prompt.txt"
            department_prompt = load_prompt(prompt_file)
            basic_prompt = load_prompt("util/basic_prompt.txt")
            current_time = get_local_time()
            combined_prompt = f"{department_prompt}\n\n{basic_prompt.format(current_time=current_time)}\n\n{text}"
            chat_model = ChatOpenAI(api_key=st.secrets["OPENAI_API_KEY"], model="gpt-4o", temperature=0)
            prompt_template = ChatPromptTemplate.from_template(combined_prompt)
            llm_chain = prompt_template | chat_model | StrOutputParser()
            try:
                summary_text = llm_chain.invoke({})
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

st.title("Gesprekssamenvatter - testversie 0.1.8.")
department = st.selectbox("Kies je afdeling", ["Bedrijven", "Financieel Advies", "Schadeafdeling", "Algemeen", "Arbo", "Algemene samenvatting", "Ondersteuning Bedrijfsarts", "Onderhoudsadviesgesprek in tabelvorm"])

if department in ["Bedrijven", "Financieel Advies", "Schadeafdeling", "Algemeen", "Arbo", "Algemene samenvatting", "Ondersteuning Bedrijfsarts", "Onderhoudsadviesgesprek in tabelvorm"]:
    st.subheader("Vragen om in je input te overwegen:")
    questions = load_questions(f"{department.lower().replace(' ', '_')}.txt")
    for question in questions:
        st.text(f"- {question.strip()}")

input_method = st.radio("Wat wil je laten samenvatten?", ["Upload tekst", "Upload audio", "Voer tekst in of plak tekst", "Neem audio op"])

if input_method == "Upload tekst":
    uploaded_file = st.file_uploader("Choose a file")
    if uploaded_file is not None:
        if uploaded_file.name.endswith('.docx'):
            with tempfile.NamedTemporaryFile(delete=False, suffix=".docx") as tmp_docx:
                tmp_docx.write(uploaded_file.getvalue())
                tmp_docx_path = tmp_docx.name
            text = read_docx(tmp_docx_path)
            os.remove(tmp_docx_path)
        else:
            text = uploaded_file.getvalue().decode("utf-8")
        summary = summarize_text(text, department)
        if summary:
            st.markdown(f"**{summary}**", unsafe_allow_html=True)

elif input_method == "Voer tekst in of plak tekst":
    text = st.text_area("Voeg tekst hier in:", height=300)
    if st.button("Samenvatten"):
        if text:
            summary = summarize_text(text, department)
            if summary:
                st.markdown(f"**Samenvatting:**\n{summary}", unsafe_allow_html=True)
                update_gesprekslog(text, summary)
            else:
                st.error("Er is een fout opgetreden bij het genereren van de samenvatting.")
        else:
            st.warning("Voer alstublieft wat tekst in om te samenvatten.")

elif input_method in ["Upload audio", "Neem audio op"]:
    uploaded_audio = None
    if input_method == "Upload audio":
        uploaded_file = st.file_uploader("Upload an audio file", type=['wav', 'mp3', 'mp4', 'm4a', 'ogg', 'webm'])
        if uploaded_file is not None:
            with st.spinner("Voorbereiden van het audiobestand, dit kan langer duren bij langere opnames..."):
                with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp_audio:
                    tmp_audio.write(uploaded_file.getvalue())
                    tmp_audio.flush()
            transcript = transcribe_audio(tmp_audio.name)
            summary = summarize_text(transcript, department)
            update_gesprekslog(transcript, summary)
            st.markdown(f"**Transcript:**\n{transcript}", unsafe_allow_html=True)
            if summary:
                st.markdown(f"**Samenvatting:**\n{summary}", unsafe_allow_html=True)
            os.remove(tmp_audio.name)
    elif input_method == "Neem audio op":
        audio_data = mic_recorder(key="recorder", start_prompt="Start opname", stop_prompt="Stop opname", use_container_width=True, format="webm")
        if audio_data and 'bytes' in audio_data:
            uploaded_audio = audio_data['bytes']
        if uploaded_audio is not None:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp_audio:
                tmp_audio.write(uploaded_audio)
                tmp_audio.flush()
                transcript = transcribe_audio(tmp_audio.name)
                summary = summarize_text(transcript, department)
                update_gesprekslog(transcript, summary)
                st.markdown(f"**Transcript:**\n{transcript}", unsafe_allow_html=True)
                if summary:
                    st.markdown(f"**Samenvatting:**\n{summary}", unsafe_allow_html=True)
                os.remove(tmp_audio.name)
        else:
            if input_method == "Upload audio":
                st.warning("Upload een audio bestand.")

st.subheader("Laatste vijf gesprekken (verdwijnen na herladen pagina!)")
for gesprek in st.session_state['gesprekslog']:
    with st.expander(f"Gesprek op {gesprek['time']}"):
        st.text_area("Transcript", value=gesprek['transcript'], height=100, key=f"trans_{gesprek['time']}")
        st.markdown("""
            <style>
            .divider {
                margin-top: 1rem;
                margin-bottom: 1rem;
                border-top: 3px solid #bbb;
            }
            </style>
            <div class="divider"></div>
            """, unsafe_allow_html=True)
        st.text_area("Samenvatting", value=gesprek['summary'], height=100, key=f"sum_{gesprek['time']}")
