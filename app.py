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
from tenacity import retry, stop_after_attempt, wait_exponential
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

def send_feedback_email(transcript, summary, feedback, additional_feedback, user_first_name=""):
    try:
        email_secrets = st.secrets["email"]
        user_email = email_secrets.get("receiving_email")
        if not user_email:
            st.error("Email receiving address is not configured properly.")
            return
        
        msg = MIMEMultipart()
        msg['From'] = email_secrets["username"]
        msg['To'] = user_email
        msg['Subject'] = "New Feedback Submission - Gesprekssamenvatter"
        
        body = f"""
        Transcript: {transcript}
        
        Summary: {summary}
        
        Feedback: {feedback}
        
        User First Name: {user_first_name if user_first_name else "Not provided"}
        
        Additional Feedback: {additional_feedback}
        """
        msg.attach(MIMEText(body, 'plain'))
        
        server = smtplib.SMTP(email_secrets["smtp_server"], int(email_secrets["smtp_port"]))
        server.starttls()
        server.login(email_secrets["username"], email_secrets["password"])
        text = msg.as_string()
        server.sendmail(email_secrets["username"], user_email, text)
        server.quit()
        return True
    except Exception as e:
        st.error(f"An error occurred while sending feedback: {str(e)}")
        return False

def feedback_form():
    with st.expander("Geef feedback"):
        with st.form(key="feedback_form"):
            user_first_name = st.text_input("Uw voornaam (verplicht bij feedback):")
            feedback = st.radio("Was dit antwoord nuttig?", ["Positief", "Negatief"])
            additional_feedback = st.text_area("Laat aanvullende feedback achter:")
            submit_button = st.form_submit_button(label="Verzenden")

            if submit_button:
                if not user_first_name:
                    st.warning("Voornaam is verplicht bij het geven van feedback.", icon="⚠️")
                else:
                    success = send_feedback_email(
                        transcript=st.session_state.get('transcript', ''),
                        summary=st.session_state.get('summary', ''),
                        feedback=feedback,
                        additional_feedback=additional_feedback,
                        user_first_name=user_first_name
                    )
                    if success:
                        st.success("Bedankt voor uw feedback!")
                    else:
                        st.error("Er is een fout opgetreden bij het verzenden van de feedback. Probeer het later opnieuw.")

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
if 'transcription_done' not in st.session_state:
    st.session_state['transcription_done'] = False
if 'summarization_done' not in st.session_state:
    st.session_state['summarization_done'] = False
if 'processing_complete' not in st.session_state:
    st.session_state['processing_complete'] = False

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

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
def summarize_chunk(chunk, department):
    chat_model = ChatOpenAI(api_key=st.secrets["OPENAI_API_KEY"], model="gpt-4", temperature=0)
    prompt_template = ChatPromptTemplate.from_template(f"Summarize the following text:\n\n{chunk}")
    llm_chain = prompt_template | chat_model | StrOutputParser()
    return llm_chain.invoke({})

def load_prompt(file_name):
    path = os.path.join(PROMPTS_DIR, file_name)
    if not os.path.exists(path):
        st.error(f"Bestand niet gevonden: {path}")
        raise FileNotFoundError(f"Bestand niet gevonden: {path}")
    with open(path, "r", encoding="utf-8") as file:
        return file.read()

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
        combined_prompt = f"{department_prompt}\n\n{basic_prompt.format(current_time=current_time)}\n\n{{text}}"
        
        chat_model = ChatOpenAI(api_key=st.secrets["OPENAI_API_KEY"], model="gpt-4o", temperature=0)
        prompt_template = ChatPromptTemplate.from_template(combined_prompt)
        llm_chain = prompt_template | chat_model | StrOutputParser()
        
        chunk_size = 4000  # Adjust based on your model's token limit
        chunks = [text[i:i+chunk_size] for i in range(0, len(text), chunk_size)]
        
        summaries = []
        progress_bar = st.progress(0)
        for i, chunk in enumerate(chunks):
            try:
                summary = llm_chain.invoke({"text": chunk})
                summaries.append(summary)
            except Exception as e:
                st.error(f"Error summarizing chunk {i+1}/{len(chunks)}: {str(e)}")
            progress_bar.progress((i + 1) / len(chunks))
        
        # Summarize the summaries
        final_summary = llm_chain.invoke({"text": "\n".join(summaries)})
        
        return final_summary

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
    
    st.title("Gesprekssamenvatter - 0.2.1")

    st.markdown("""
    <style>
    .main {
        background-color: #f0f8ff;
        color: #333;
        font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
    }
    .stButton>button {
        background-color: #4CAF50;
        color: white;
        border: none;
        padding: 12px 28px;
        text-align: center;
        text-decoration: none;
        display: inline-block;
        font-size: 16px;
        margin: 4px 2px;
        cursor: pointer;
        border-radius: 30px;
        transition: all 0.3s ease 0s;
        box-shadow: 0 8px 15px rgba(0, 0, 0, 0.1);
    }
    .stButton>button:hover {
        background-color: #45a049;
        box-shadow: 0 15px 20px rgba(46, 229, 157, 0.4);
        transform: translateY(-7px);
    }
    .summary-box {
        border: none;
        border-radius: 15px;
        padding: 25px;
        margin: 20px 0;
        background-color: #ffffff;
        box-shadow: 0 10px 30px rgba(0, 0, 0, 0.1);
        transition: all 0.3s ease;
    }
    .summary-box:hover {
        box-shadow: 0 15px 40px rgba(0, 0, 0, 0.15);
        transform: translateY(-5px);
    }
    .summary-box h3 {
        color: #2c3e50;
        border-bottom: 2px solid #3498db;
        padding-bottom: 10px;
        margin-bottom: 20px;
        text-align: center;
        font-weight: 600;
    }
    .content {
        white-space: pre-wrap;
        word-wrap: break-word;
        font-size: 16px;
        line-height: 1.8;
        color: #34495e;
    }
    .transcript-box {
        border: none;
        border-radius: 10px;
        padding: 15px;
        margin-bottom: 20px;
        background-color: #f9f9f9;
        box-shadow: 0 5px 15px rgba(0, 0, 0, 0.05);
    }
    .copy-button {
        text-align: center;
        margin-top: 20px;
    }
    .stProgress > div > div > div > div {
        background-color: #3498db;
    }
    .stSelectbox {
        color: #2c3e50;
    }
    .stSelectbox > div > div {
        background-color: #ffffff;
        border-radius: 5px;
    }
    .stRadio > div {
        background-color: #ffffff;
        border-radius: 5px;
        padding: 10px;
        box-shadow: 0 2px 5px rgba(0, 0, 0, 0.05);
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
            if st.button("Samenvatten", key='summarize_button'):
                if st.session_state['input_text']:
                    st.session_state['transcript'] = st.session_state['input_text']
                    st.session_state['summary'] = summarize_text(st.session_state['transcript'], st.session_state['department'])
                    update_gesprekslog(st.session_state['transcript'], st.session_state['summary'])
                else:
                    st.warning("Voer alstublieft wat tekst in om te samenvatten.")

        elif st.session_state['input_method'] in ["Upload audio", "Neem audio op"]:
            if not st.session_state['processing_complete']:
                if st.session_state['input_method'] == "Upload audio":
                    uploaded_file = st.file_uploader("Upload an audio file", type=['wav', 'mp3', 'mp4', 'm4a', 'ogg', 'webm'])
                    if uploaded_file is not None and not st.session_state['transcription_done']:
                        with st.spinner("Transcriberen van audio..."):
                            with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp_audio:
                                tmp_audio.write(uploaded_file.getvalue())
                                tmp_audio.flush()
                            st.session_state['transcript'] = transcribe_audio(tmp_audio.name)
                            os.remove(tmp_audio.name)
                        st.session_state['transcription_done'] = True
                        st.rerun()
                elif st.session_state['input_method'] == "Neem audio op":
                    audio_data = mic_recorder(key="recorder", start_prompt="Start opname", stop_prompt="Stop opname", use_container_width=True, format="webm")
                    if audio_data and 'bytes' in audio_data and not st.session_state['transcription_done']:
                        with st.spinner("Transcriberen van audio..."):
                            with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp_audio:
                                tmp_audio.write(audio_data['bytes'])
                                tmp_audio.flush()
                            st.session_state['transcript'] = transcribe_audio(tmp_audio.name)
                            os.remove(tmp_audio.name)
                        st.session_state['transcription_done'] = True
                        st.rerun()
                
                if st.session_state['transcription_done'] and not st.session_state['summarization_done']:
                    with st.spinner("Genereren van samenvatting..."):
                        st.session_state['summary'] = summarize_text(st.session_state['transcript'], st.session_state['department'])
                    update_gesprekslog(st.session_state['transcript'], st.session_state['summary'])
                    st.session_state['summarization_done'] = True
                    st.session_state['processing_complete'] = True
                    st.rerun()

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

            if st.button("Kopieer naar klembord", key='copy_clipboard_button'):
                copy_to_clipboard(st.session_state['transcript'], st.session_state['summary'])
            if st.session_state.get('summary'):
                feedback_form() 

    # Display conversation history
    st.subheader("Laatste vijf gesprekken")
    for i, gesprek in enumerate(st.session_state['gesprekslog']):
        with st.expander(f"Gesprek {i+1} op {gesprek['time']}"):
            st.markdown("**Transcript:**")
            st.markdown(f'<div class="content">{html.escape(gesprek["transcript"])}</div>', unsafe_allow_html=True)
            st.markdown("**Samenvatting:**")
            st.markdown(gesprek["summary"], unsafe_allow_html=True)

    # Reset flags if input method changes
    if st.session_state['input_method'] not in ["Upload audio", "Neem audio op"]:
        st.session_state['transcription_done'] = False
        st.session_state['summarization_done'] = False
        st.session_state['processing_complete'] = False

if __name__ == "__main__":
    main()