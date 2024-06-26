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
from streamlit_option_menu import option_menu
from streamlit_lottie import st_lottie
import requests
import json

def load_lottie_url(url: str):
    r = requests.get(url)
    if r.status_code != 200:
        return None
    return r.json()

def set_background(image_file):
    with open(image_file, "rb") as f:
        img_data = f.read()
    b64_encoded = base64.b64encode(img_data).decode()
    style = f"""
        <style>
        .stApp {{
            background-image: url(data:image/png;base64,{b64_encoded});
            background-size: cover;
        }}
        </style>
    """
    st.markdown(style, unsafe_allow_html=True)


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
    
    # Set a subtle background image
    set_background('path_to_your_background_image.png')  # Replace with actual path

    # Custom CSS for a modern, sleek design
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@400;600&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Poppins', sans-serif;
    }
    
    .main {
        background-color: rgba(255,255,255,0.9);
        border-radius: 20px;
        padding: 2rem;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    }
    
    h1, h2, h3 {
        color: #1e3a8a;
    }
    
    .stButton>button {
        border-radius: 50px;
        padding: 0.5rem 2rem;
        font-weight: 600;
        background-color: #3b82f6;
        color: white;
        border: none;
        transition: all 0.3s ease;
    }
    
    .stButton>button:hover {
        background-color: #2563eb;
        transform: translateY(-2px);
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    }
    
    .stTextInput>div>div>input {
        border-radius: 50px;
    }
    
    .stTextArea>div>div>textarea {
        border-radius: 15px;
    }
    
    .feedback-card {
        background-color: white;
        border-radius: 15px;
        padding: 2rem;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        margin-top: 2rem;
    }
    
    .css-1d391kg {
        padding-top: 3.5rem;
    }
    </style>
    """, unsafe_allow_html=True)

    # Animated logo
    lottie_url = "https://assets5.lottiefiles.com/packages/lf20_bsPjV4.json"  # Replace with a more suitable animation
    lottie_json = load_lottie_url(lottie_url)
    
    col1, col2 = st.columns([1, 3])
    with col1:
        st_lottie(lottie_json, speed=1, height=150, key="logo")
    with col2:
        st.title("Gesprekssamenvatter")
        st.subheader("Vereenvoudig uw gesprekken met AI")

    # Modern navigation
    selected = option_menu(
        menu_title=None,
        options=["Transcriberen", "Samenvatten", "Feedback"],
        icons=["mic", "file-text", "chat-dots"],
        menu_icon="cast",
        default_index=0,
        orientation="horizontal",
        styles={
            "container": {"padding": "0!important", "background-color": "#f0f9ff"},
            "icon": {"color": "#3b82f6", "font-size": "20px"}, 
            "nav-link": {"font-size": "16px", "text-align": "center", "margin":"0px", "--hover-color": "#eee"},
            "nav-link-selected": {"background-color": "#3b82f6", "color": "white"},
        }
    )

    if selected == "Transcriberen":
        st.header("Transcribeer uw gesprek")
        
        input_method = st.radio(
            "Hoe wilt u uw gesprek invoeren?",
            ("Audio opnemen", "Audio uploaden", "Tekst invoeren"),
            horizontal=True
        )

        if input_method == "Audio opnemen":
            # Use your existing audio recording functionality here
            audio_bytes = audio_recorder(
                key="audio_recorder",
                text="Klik om op te nemen",
                recording_color="#e74c3c",
                neutral_color="#3498db",
                icon_name="microphone",
                icon_size="6x"
            )
            if audio_bytes:
                st.audio(audio_bytes, format="audio/wav")
                if st.button("Transcriberen", key="transcribe_recorded"):
                    # Use your existing transcription function here
                    st.session_state['transcript'] = transcribe_audio(audio_bytes)
                    st.success("Transcriptie voltooid!")

        elif input_method == "Audio uploaden":
            uploaded_file = st.file_uploader("Upload een audiobestand", type=['mp3', 'wav', 'm4a'])
            if uploaded_file is not None:
                if st.button("Transcriberen", key="transcribe_uploaded"):
                    # Use your existing transcription function here
                    st.session_state['transcript'] = transcribe_audio(uploaded_file)
                    st.success("Transcriptie voltooid!")

        else:
            st.session_state['input_text'] = st.text_area("Voer uw gesprekstekst in", height=300)
            if st.button("Verwerken", key="process_text"):
                st.session_state['transcript'] = st.session_state['input_text']
                st.success("Tekst verwerkt!")

    elif selected == "Samenvatten":
        st.header("Vat uw gesprek samen")
        
        if 'transcript' in st.session_state and st.session_state['transcript']:
            st.text_area("Transcript", st.session_state['transcript'], height=200)
            
            if st.button("Samenvatten", key="summarize"):
                # Use your existing summarization function here
                st.session_state['summary'] = summarize_text(st.session_state['transcript'], st.session_state['department'])
                st.success("Samenvatting gegenereerd!")
            
            if 'summary' in st.session_state and st.session_state['summary']:
                st.markdown("### Samenvatting")
                st.write(st.session_state['summary'])
        else:
            st.warning("Transcribeer eerst een gesprek voordat u het samenvat.")

    elif selected == "Feedback":
        st.header("Geef ons feedback")
        
        with st.form(key="feedback_form"):
            user_name = st.text_input("Uw naam")
            feedback_type = st.radio("Hoe was uw ervaring?", ["Positief", "Negatief"])
            feedback_text = st.text_area("Uw feedback (optioneel)")
            submit_button = st.form_submit_button(label="Verstuur feedback")

            if submit_button:
                if user_name:
                    # Use your existing feedback submission function here
                    send_feedback_email(
                        transcript=st.session_state.get('transcript', ''),
                        summary=st.session_state.get('summary', ''),
                        feedback=feedback_type,
                        additional_feedback=feedback_text,
                        user_first_name=user_name
                    )
                    st.success("Bedankt voor uw feedback!")
                else:
                    st.error("Vul alstublieft uw naam in.")

    # Footer
    st.markdown("---")
    st.markdown("Wat vind je van deze tool? Laat het me weten middels de feedbackfunctie. Bedankt!")

if __name__ == "__main__":
    main()