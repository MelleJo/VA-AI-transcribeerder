import streamlit as st
from openai import OpenAI
from streamlit_mic_recorder import mic_recorder
import os
import time
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



client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

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
    return vertaling.get(dag_engels, dag_engels)  # Geeft de Nederlandse dag terug, of de Engelse als niet gevonden

def split_audio(file_path, max_size=24000000):
    audio = AudioSegment.from_file(file_path)
    duration = len(audio)
    chunks_count = max(1, duration // (max_size / (len(audio.raw_data) / duration)))

    # Als chunks_count 1 is, retourneer de hele audio in één stuk
    if chunks_count == 1:
        return [audio]

    # Anders, splits de audio in de berekende aantal chunks
    return [audio[i:i + duration // chunks_count] for i in range(0, duration, duration // int(chunks_count))]

# def copy_function():
    if 'summary' in st.session_state and st.session_state['summary']:
        summary = st.session_state['summary']
        # HTML en JavaScript voor de knop, met Streamlit-achtige styling
        styled_button_html = f"""
        <html>
        <head>
        <style>
            .copy-btn {{
                color: #ffffff;
                background-color: #4CAF50;
                padding: 0.25em 0.75em;
                font-size: 16px;
                border: none;
                border-radius: 4px;
                cursor: pointer;
                margin: 2px;
                transition: background-color 0.3s;
            }}
            .copy-btn:hover {{
                background-color: #45a049;
            }}
        </style>
        </head>
        <body>
        <button class="copy-btn" onclick='navigator.clipboard.writeText(`{summary}`)'>Kopieer</button>
        <script>
        const copyBtn = document.querySelector('.copy-btn');
        copyBtn.addEventListener('click', function(event) {{
        alert('Samenvatting gekopieërd!');
        }});
        </script>
        </body>
        </html>
        """
        components.html(styled_button_html, height=50)



if 'gesprekslog' not in st.session_state:
    st.session_state['gesprekslog'] = []

def get_local_time():
    timezone = pytz.timezone("Europe/Amsterdam")
    return datetime.now(timezone).strftime('%d-%m-%Y %H:%M:%S')

def transcribe_audio(file_path):
    with st.spinner("Transcriptie maken..."): 
        transcript_text = ""
        try:
            audio_segments = split_audio(file_path)
            for segment in audio_segments:
                with tempfile.NamedTemporaryFile(delete=True, suffix='.wav') as temp_file:
                    segment.export(temp_file.name, format="wav")
                    with open(temp_file.name, "rb") as audio_file:
                        transcription_response = client.audio.transcriptions.create(file=audio_file, model="whisper-1")
                        if hasattr(transcription_response, 'text'):
                            transcript_text += transcription_response.text + " "
            return transcript_text.strip()
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
        "Wat zijn de actiepunten voor de klant, wat zijn de actiepunten voor de collega, of voor jezelf?",
        "Wat moet er in de agenda komen en wanneer?"
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
    ],
    "Arbo": [
    "Wanneer heeft het gesprek plaatsgevonden?",
    "Wie heb je gesproken?",
    "Waarom hebben jullie elkaar gesproken?",
    "Wat is er inhoudelijk besproken, en zijn er afspraken gemaakt?",
    "Actiepunten: Voor jezelf, de andere partij, of naar een collega toe?"
    ]

}

def read_docx(file_path):
    doc = Document(file_path)
    fullText = []
    for para in doc.paragraphs:
        fullText.append(para.text)
    return '\n'.join(fullText)

def summarize_text(text, department):
    with st.spinner("Samenvatting maken..."):
        department_prompts = {
            "Bedrijven": "Als expert in het samenvatten van zakelijke verzekeringsgesprekken, focus je op mutaties of wijzigingen in verzekeringen en adviesprocessen. Documenteer klantbehoeften, de rationale achter adviezen, en de besproken verzekeringsproducten. Belicht actiepunten uit het gesprek en leg besluitvorming vast. Zorg ervoor dat je samenvatting helder de klantvraag, het gegeven advies, en concrete actiepunten bevat, inclusief de datum en tijd van het gesprek.",
            "Financieel Advies": "Je bent gespecialiseerd in het samenvatten van financieel adviesgesprekken. Jouw doel is om de financiële doelstellingen van de klant, de besproken financiële producten, en het gegeven advies helder te documenteren. Zorg voor een beknopte samenvatting die de kernpunten en aanbevelingen omvat.",
            "Schadeafdeling": "Als expert in het documenteren van gesprekken over schademeldingen, leg je de focus op de details van de schade, het object, de timing, en de ondernomen stappen. Samenvat deze tekst door de schadeomvang, betrokken objecten, en de actiepunten voor zowel de klant als de schadebehandelaar duidelijk te maken.",
            "Algemeen": "Je bent een expert in het samenvatten van algemene klantvragen en gesprekken. Jouw taak is om specifieke details, klantvragen, en relevante actiepunten te identificeren en te documenteren. Zorg voor een duidelijke en gestructureerde samenvatting die de belangrijkste punten en eventuele vervolgstappen bevat.",
            "Arbo": "Als expert in het samenvatten van Arbo-gerelateerde gesprekken, focus je op de vastlegging van notities over arbogesprekken of andere onderwerpen rondom casemanagement. Je zorgt ervoor dat details goed worden vastgelegd. Je let extra goed op wie er is gesproken, wat er is besproken, wat voor afspraken er zijn gemaakt, en wat is er inhoudelijk besproken. Samenvat deze tekst met aandacht voor de essentiële actiepunten en besluitvorming."
        }

        current_time = get_local_time()
        basic_prompt = (
            f"Vandaag is {current_time}. Benut deze informatie om een accurate en "
            "gedetailleerde samenvatting, zo kort mogelijk met zo min mogelijk woorden, maar wel met alle details. "
            "Begin met de exacte datum en tijd van het gesprek. "
            "Identificeer het onderwerp van het gesprek. Detailleer het klantverzoek met "
            "alle details, inclusief eventuele zorgen of verzoeken om wijzigingen. "
            "Beschrijf het advies dat is gegeven en alternatieven die zijn voorgesteld. Specificeer de actiepunten "
            "die zijn overeengekomen, inclusief eventuele deadlines."
            "Handhaaf een coherente, objectieve en complete weergave van het gesprek."
            "Verzin niets extra's, als alle belangrijke punten en details zijn aangegeven is het klaar."
            "Als er iets niet is genoemd, dan hoef je dit ook niet over te nemen in de samenvatting."
        )

        combined_prompt = f"{department_prompts.get(department, '')}\n\n{basic_prompt}\n\n{text}"

        chat_model = ChatOpenAI(api_key=st.secrets["OPENAI_API_KEY"], model="gpt-4-0125-preview", temperature=0)
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
    
    if summary:
        # HTML en JavaScript voor de knop, met Streamlit-achtige styling
        styled_button_html = f"""
        <html>
        <head>
        <style>
            .copy-btn {{
                color: #ffffff;
                background-color: #4CAF50;
                padding: 0.25em 0.75em;
                font-size: 16px;
                border: none;
                border-radius: 4px;
                cursor: pointer;
                margin: 2px;
                transition: background-color 0.3s;
            }}
            .copy-btn:hover {{
                background-color: #45a049;
            }}
        </style>
        </head>
        <body>
        <input type="text" value="{summary}" id="summaryText" style="width:90%;margin-bottom:10px;">
        <button class="copy-btn" onclick='navigator.clipboard.writeText(document.getElementById("summaryText").value)'>Kopieer</button>
        <script>
        const copyBtn = document.querySelector('.copy-btn');
        copyBtn.addEventListener('click', function(event) {{
        alert('Samenvatting gekopieërd!');
        }});
        </script>
        </body>
        </html>
        """
        components.html(styled_button_html, height=100)
    
    

# Aanroepen na het genereren van de samenvatting
def update_gesprekslog(transcript, summary):
    current_time = get_local_time()  # Gebruikt nu NL standaard voor tijdmarkering
    st.session_state.gesprekslog.insert(0, {'time': current_time, 'transcript': transcript, 'summary': summary})
    st.session_state.gesprekslog = st.session_state.gesprekslog[:5]




st.title("Gesprekssamenvatter - testversie 0.1.5.")

department = st.selectbox("Kies je afdeling", ["Bedrijven", "Financieel Advies", "Schadeafdeling", "Algemeen", "Arbo"])

if department in department_questions:
    st.subheader("Vragen om in je input te overwegen:")
    for question in department_questions[department]:
        st.text(f"- {question}")

input_method = st.radio("Wat wil je laten samenvatten?", ["Upload tekst", "Upload audio", "Voer tekst in of plak tekst", "Neem audio op"])

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
            #st.button("Copy to Clipboard", on_click=copy_function)

elif input_method == "Voer tekst in of plak tekst":
    text = st.text_area("Voeg tekst hier in:", height=300)  # Maakt een tekstveld waar gebruikers tekst kunnen invoeren
    if st.button("Samenvatten"):  # Een knop die gebruikers kunnen klikken nadat ze de tekst hebben ingevoerd
        if text:  # Controleert of er tekst is ingevoerd voordat verder wordt gegaan
            summary = summarize_text(text, department)  # Roept de functie aan om de tekst samen te vatten
            if summary:
                st.markdown(f"**Samenvatting:**\n{summary}", unsafe_allow_html=True)
                update_gesprekslog(text, summary)  # Voegt dit toe aan het gesprekslog
                # st.button("Copy to Clipboard", on_click=copy_function)
            else:
                st.error("Er is een fout opgetreden bij het genereren van de samenvatting.")
        else:
            st.warning("Voer alstublieft wat tekst in om te samenvatten.")


elif input_method in ["Upload audio", "Neem audio op"]:
    # Initialiseer uploaded_audio buiten de if/elif statements voor brede scope
    uploaded_audio = None
    if input_method == "Upload audio":
        uploaded_file = st.file_uploader("Upload an audio file", type=['wav', 'mp3', 'mp4', 'm4a', 'ogg', 'webm'])
        if uploaded_file is not None:
            uploaded_audio = uploaded_file.getvalue()
    elif input_method == "Neem audio op":
        audio_data = mic_recorder(
            key="recorder",
            start_prompt="Start opname",
            stop_prompt="Stop opname",
            use_container_width=True,
            format="webm"
        )
        if audio_data and 'bytes' in audio_data:
            uploaded_audio = audio_data['bytes']
    
    # Verwerk de audio alleen als uploaded_audio is ingesteld
    if uploaded_audio is not None:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp_audio:
            tmp_audio.write(uploaded_audio)
            tmp_audio.flush()
            transcript = transcribe_audio(tmp_audio.name)
            summary = summarize_text(transcript, department)
            update_gesprekslog(transcript, summary)  # Correct aangeroepen na samenvatting
            st.markdown(f"**Transcript:**\n{transcript}", unsafe_allow_html=True)
            if summary:
                st.markdown(f"**Samenvatting:**\n{summary}", unsafe_allow_html=True)
                # st.button("Copy to Clipboard", on_click=copy_function)
            os.remove(tmp_audio.name)
    else:
        if input_method == "Upload audio":
            st.warning("Upload een audio bestand.")





    st.subheader("Laatste vijf gesprekken (verdwijnen na herladen pagina!)")

    for gesprek in st.session_state.gesprekslog:
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

