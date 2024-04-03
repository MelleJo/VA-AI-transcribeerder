import streamlit as st
from openai import OpenAI
from streamlit_mic_recorder import mic_recorder
import os
import time
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

openai.api_key = st.secrets["OPENAI_API_KEY"]
client = OpenAI(openai_api_key=api_key)

def transcribe_audio(file_path):
    try:
        transcript = client.Audio.transcribe(file=open(file_path), model="whisper-1")
        transcript_text = transcript["data"]["text"]
        return transcript_text
    except Exception as e:
        st.error(f"Transcriptie mislukt: {str(e)}")
        return "Transcriptie mislukt."

def summarize_text(text, department):
    department_prompts = {
        "Verzekeringen": """
        Je bent een expert in verzekeringen met een focus op polisvoorwaarden en dekking. Analyseer de volgende tekst en bied een beknopte samenvatting die essentiële informatie over dekkingen, uitsluitingen en voorwaarden belicht. Zorg ervoor dat je antwoord duidelijk en nauwkeurig is, met directe citaten uit de tekst waar mogelijk.
        """,
        "Financieel Advies": """
        Als financieel adviseur is jouw taak om de onderliggende financiële principes en adviezen in de volgende tekst te identificeren en samen te vatten. Focus op het verstrekken van een helder en begrijpelijk overzicht dat de kernpunten en aanbevelingen voor de lezer benadrukt.
        """,
        "Claims": """
        Analyseer de volgende tekst vanuit het perspectief van een schadebehandelaar. Je doel is om een samenvatting te geven die zich richt op claims, schadegevallen en relevante polisvoorwaarden. Vermeld specifieke dekkingen, uitsluitingen en procedures die in de tekst worden beschreven, met aandacht voor detail en nauwkeurigheid.
        """,
        "Klantenservice": """
        Als klantenservicemedewerker is jouw rol om de informatie in de volgende tekst te interpreteren en samen te vatten op een manier die voor de klant gemakkelijk te begrijpen is. Focus op het benadrukken van veelgestelde vragen, belangrijke punten en nuttige adviezen die de klant kan gebruiken.
        """
    }

    basic_prompt = "Hieronder vind je een samenvatting van de belangrijkste punten uit de tekst. Deze samenvatting is bedoeld om je een snel overzicht te geven van de inhoud, met focus op de meest relevante informatie voor jouw specifieke behoeften."

    prompt = department_prompts.get(department, "") + basic_prompt + f"\n\n{text}"
    response = openai.Completion.create(
        model="gpt-4",
        prompt=prompt,
        temperature=0.5,
        max_tokens=1024,
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

elif input_method in ["Audio uploaden", "Audio opnemen"]:
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
