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
from docx import Document

client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

def transcribe_audio(file_path):
    try:
        with open(file_path, "rb") as audio_file:
            transcription_response = client.audio.transcriptions.create(file=audio_file, model="whisper-1")
            transcript_text = transcription_response.text if hasattr(transcription_response, 'text') else "Transcript was niet gevonden."
            return transcript_text
    except Exception as e:
        st.error(f"Transcription failed: {str(e)}")
        return "Transcription mislukt."

department_questions = {
    "Bedrijven": [
        "Waarom heeft de klant gebeld?",
        "Wat is de reden voor de mutatie of wijziging in de verzekering?",
        "Welk advies is gegeven en waarom? - samenvatting van de klantbehoefte",
        "Wat is de datum?",
        "Over welk product gaat het gesprek?",
        "Wat zijn de actiepunten voor de klant, wat zijn de actiepunten voor de collega, of voor jezelf?"
    ],
    "Financieel Advies": [
        "Wat zijn de financiële doelstellingen van de klant?",
        "Welke financiële producten zijn besproken?",
        "Welk specifiek advies is gegeven?"
    ],
    "Schadeafdeling": [
        "Wanneer is de schade opgetreden?",
        "Wat betreft de schade en aan welk object?",
        "Zijn er al stappen ondernomen voor het melden van de schade?",
        "Is er een expert langsgeweest?",
        "Zijn er foto's van de schade?",
        "Wat zijn de actiepunten voor de klant?",
        "Wat zijn de actiepunten voor de schadebehandelaar?"
    ],
    "Algemeen": [
        "Wat is de algemene vraag van de klant?",
        "Zijn er specifieke details die niet overgeslagen moeten worden?",
        "Heeft de klant eerdere interacties gehad die relevant zijn?"
    ]
}

def read_docx(file_path):
    doc = Document(file_path)
    fullText = []
    for para in doc.paragraphs:
        fullText.append(para.text)
    return '\n'.join(fullText)

def summarize_text(text, department):
    # Aangepaste afdelingsspecifieke prompts
    department_prompts = {
        "Bedrijven": "Als expert in het samenvatten van zakelijke verzekeringsgesprekken, focus je op mutaties of wijzigingen in verzekeringen. Je documenteert nauwkeurig adviesprocessen, inclusief klantbehoeften, de rationale achter adviezen, en productdetails. Samenvat deze tekst met aandacht voor de essentiële actiepunten en besluitvorming:",
        "Financieel Advies": "Je bent gespecialiseerd in het samenvatten van financieel adviesgesprekken. Jouw doel is om de financiële doelstellingen van de klant, de besproken financiële producten, en het gegeven advies helder te documenteren. Zorg voor een beknopte samenvatting die de kernpunten en aanbevelingen omvat:",
        "Schadeafdeling": "Als expert in het documenteren van gesprekken over schademeldingen, leg je de focus op de details van de schade, het object, de timing, en de ondernomen stappen. Samenvat deze tekst door de schadeomvang, betrokken objecten, en de actiepunten voor zowel de klant als de schadebehandelaar duidelijk te maken:",
        "Algemeen": "Je bent een expert in het samenvatten van algemene klantvragen en gesprekken. Jouw taak is om specifieke details, klantvragen, en relevante actiepunten te identificeren en te documenteren. Zorg voor een duidelijke en gestructureerde samenvatting die de belangrijkste punten en eventuele vervolgstappen bevat:"
    }

    basic_prompt = "Hier is de input, samenvat deze tekst met zoveel mogelijk bullet points om een overzichtelijk overzicht te maken."
    combined_prompt = f"{department_prompts.get(department, '')}\n\n{basic_prompt}\n\n{text}"

    # Initialize LangChain's ChatOpenAI with the provided API key and model
    chat_model = ChatOpenAI(api_key=st.secrets["OPENAI_API_KEY"], model="gpt-4-0125-preview", temperature=0.1)

    # Creating a chain
    prompt_template = ChatPromptTemplate.from_template(combined_prompt)
    llm_chain = prompt_template | chat_model | StrOutputParser()

    # Adjusting execution and error handling to directly use the string response
    try:
        summary_text = llm_chain.invoke({})  # Directly using the response as summary_text
        if not summary_text:  # Checking if summary_text is empty or not generated
            summary_text = "Mislukt om een samenvatting te genereren."
    except Exception as e:
        st.error(f"Error generating summary: {e}")
        summary_text = "Mislukt om een samenvatting te genereren."

    return summary_text



st.title("Gesprekssamenvatter")

department = st.selectbox("Kies je afdeling", ["Bedrijven", "Financieel Advies", "Schadeafdeling", "Algemeen"])

if department in department_questions:
    st.subheader("Vragen om in je input te overwegen:")
    for question in department_questions[department]:
        st.text(f"- {question}")

input_method = st.radio("Wat wil je laten samenvatten?", ["Upload tekst", "Upload Audio", "Voer tekst in of plak tekst", "Neem audio op"])

if input_method == "Upload tekst":
    uploaded_file = st.file_uploader("Choose a file")
    if uploaded_file is not None:
        # Check the file extension
        if uploaded_file.name.endswith('.docx'):
    # Handle Word documents (.docx)
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
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp_audio:
            if input_method == "Upload Audio":
                tmp_audio.write(uploaded_audio.getvalue())
            else:
                tmp_audio.write(uploaded_audio)
            tmp_audio.flush()
            transcript = transcribe_audio(tmp_audio.name)
            summary = summarize_text(transcript, department)
            st.markdown(f"**Transcript:**\n{transcript}", unsafe_allow_html=True)
            if summary:
                st.markdown(f"**Samenvatting:**\n{summary}", unsafe_allow_html=True)


            os.remove(tmp_audio.name)
    elif input_method == "Upload Audio":
        st.warning("Upload een audio bestand.")

elif input_method == "Voer tekst in of plak tekst":
    text = st.text_area("Enter or paste the text here:")
    if st.button("Samenvatten"):
        summary = summarize_text(text, department)
        if summary:
            st.markdown(f"**Samenvatting:**\n{summary}", unsafe_allow_html=True)
        