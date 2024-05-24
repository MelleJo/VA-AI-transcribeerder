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
    detailed_prompt = f"""
    Maak een gedetailleerd verslag op basis van de volgende informatie over een werknemer, zonder specifieke medische details te onthullen. Het verslag moet de volgende secties bevatten:
    
    1. Introductie en Basisgegevens van de Werknemer:
    [Introductie van de werknemer, functie, en normale werkuren]

    2. Details over de Huidige Gezondheidstoestand:
    [Algemene beschrijving van de gezondheidstoestand zonder specifieke medische details, zoals aanhoudende vermoeidheid en stressgerelateerde symptomen]

    3. Overzicht van de Werkrelatie en Huidige Werkomstandigheden:
    [Beschrijving van de werkrelatie en huidige omstandigheden op het werk, inclusief besprekingen over aanpassingen in werklast of werkuren]

    4. Advies voor Werkhervatting en Aanpassingen aan de Werkplek:
    [Adviezen voor aanpassingen aan de werkplek en strategieën voor een geleidelijke terugkeer naar werk]

    Gesprekstekst:
    {text}
    """
    
    chat_model = ChatOpenAI(api_key=st.secrets["OPENAI_API_KEY"], model="gpt-4-0125-preview", temperature=0)
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
    detailed_prompt = f"""
    Maak een beknopte en duidelijke samenvatting van het onderhoudsadviesgesprek in tabelvorm. Zorg ervoor dat de samenvatting de volgende secties bevat:

    **Datum**:
    [Datum van het gesprek]

    **Aanwezig**:
    - [Namen van de aanwezigen]

    **Introductie**:
    Geef een korte introductie van de context van het gesprek en de reden waarom het gesprek plaatsvond.

    **Situatie**:
    Beschrijf de huidige situatie van de klant en eventuele veranderingen die relevant zijn voor de verzekeringen.

    **Risico's**:
    Beschrijf de besproken risico's die relevant zijn voor de verzekeringen van de klant.

    **Zakelijke Risico's**:

    | Risico                        | Besproken | Actie                             | Actie voor    |
    |-------------------------------|-----------|-----------------------------------|---------------|
    | [Risico 1]                    | [Ja/Nee]  | [Actie]                           | [Persoon]     |
    | [Risico 2]                    | [Ja/Nee]  | [Actie]                           | [Persoon]     |
    | [Risico 3]                    | [Ja/Nee]  | [Actie]                           | [Persoon]     |
    | [Risico 4]                    | [Ja/Nee]  | [Actie]                           | [Persoon]     |
    | [Risico 5]                    | [Ja/Nee]  | [Actie]                           | [Persoon]     |

    **Privé Risico's**:

    | Risico | Besproken | Actie | Actie voor |
    |--------|-----------|-------|------------|
    | [Risico 1] | [Ja/Nee] | [Actie] | [Persoon] |
    | [Risico 2] | [Ja/Nee] | [Actie] | [Persoon] |

    **Gesprekstekst**:
    {text}
    """
    
    chat_model = ChatOpenAI(api_key=st.secrets["OPENAI_API_KEY"], model="gpt-4-0125-preview", temperature=0)
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


department_questions = {
    "Bedrijven": [
        "Waarom heeft de klant gebeld?",
        "Wat is de reden voor de mutatie of wijziging in de verzekering?",
        "Welk advies is gegeven en waarom?",
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
    ],
    "Algemene samenvatting": [
        "Wat zijn de belangrijkste details?"
    ],
    "Ondersteuning Bedrijfsarts": [
        "Voorstellen en introductie",
        "Functie en werkuren per week",
        "Huidige gezondheidssituatie",
        "Lopende behandelingen",
        "Medicatie",
        "Vooruitzichten",
        "Contact met werk",
        "Werkhervattingsadvies",
        "Uitleg over vervolgproces"
    ],
    "Onderhoudsadviesgesprek in tabelvorm": [
        "Welke verzekeringen zijn besproken?",
        "Welke risico's zijn besproken?",
        "Welk specifiek advies is gegeven?",
        "Zijn er belangrijke dingen die veranderen?",
        "Moet er iets gewijzigd worden?"
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
            department_prompts = {
                "Bedrijven": "Als expert in het samenvatten van zakelijke verzekeringsgesprekken, focus je op mutaties of wijzigingen in verzekeringen en adviesprocessen...",
                "Financieel Advies": "Je bent gespecialiseerd in het samenvatten van financieel adviesgesprekken. Jouw doel is om de financiële doelstellingen van de klant, de besproken financiële producten, en het gegeven advies helder te documenteren. Zorg voor een beknopte samenvatting die de kernpunten en aanbevelingen omvat.",
                "Schadeafdeling": "Als expert in het documenteren van gesprekken over schademeldingen, leg je de focus op de details van de schade, het object, de timing, en de ondernomen stappen. Samenvat deze tekst door de schadeomvang, betrokken objecten, en de actiepunten voor zowel de klant als de schadebehandelaar duidelijk te maken.",
                "Algemeen": "Je bent een expert in het samenvatten van algemene klantvragen en gesprekken. Jouw taak is om specifieke details, klantvragen, en relevante actiepunten te identificeren en te documenteren. Zorg voor een duidelijke en gestructureerde samenvatting die de belangrijkste punten en eventuele vervolgstappen bevat.",
                "Arbo": "Als expert in het samenvatten van Arbo-gerelateerde gesprekken, focus je op de vastlegging van notities over arbogesprekken of andere onderwerpen rondom casemanagement. Je zorgt ervoor dat details goed worden vastgelegd. Je let extra goed op wie er is gesproken, wat er is besproken, wat voor afspraken er zijn gemaakt, en wat is er inhoudelijk besproken. Samenvat deze tekst met aandacht voor de essentiële actiepunten en besluitvorming.",
                "Algemene samenvatting": "Jij bent een expert in het samenvatten van elk soort notitie, gesprek of wat er ook maar wordt aangeleverd. Je geeft een complete samenvatting, met specifiek oog voor de details, maar je vermijdt herhaling en probeert ervoor te zorgen dat de samenvatting beknopt is. Maar volledigheid gaat altijd boven de beknoptheid. Je zorgt ervoor dat alle afspraken, actiepunten en andere elementen duidelijk worden overgenomen. Het moet zo zijn dat als iemand de notitie leest, hij/zij net zoveel weet als wanneer hij bij het gesprek was."
            }
            current_time = get_local_time()
            basic_prompt = (
                f"Vandaag is {current_time}. Vermeld dit altijd in de titel. Benut deze informatie om een accurate en "
                "gedetailleerde samenvatting, zo kort mogelijk met zo min mogelijk woorden, maar wel met alle details. "
                "Begin met de exacte datum en tijd van het gesprek. "
                "Identificeer het onderwerp van het gesprek. Detailleer het klantverzoek met "
                "alle details, inclusief eventuele zorgen of verzoeken om wijzigingen. "
                "Beschrijf het advies dat is gegeven en alternatieven die zijn voorgesteld. Specificeer de actiepunten "
                "die zijn overeengekomen, inclusief eventuele deadlines."
                "Handhaaf een coherente, objectieve en complete weergave van het gesprek."
                "Verzin niets extra's, als alle belangrijke punten en details zijn aangegeven is het klaar."
                "Als er iets niet is genoemd, dan hoef je dit ook niet over te nemen in de samenvatting."
                "Je hoeft geen disclaimer, of deadlines aan te geven op het moment dat er geen deadlines zijn gegeven."
                "Je noemt alleen dingen uit het gesprek, dus als er bijvoorbeeld geen advies is gegeven, of geen actiepunten die je kunt herleiden, dan noem je ook niet dat er geen adviezen of actiepunten zijn.",
                "De taal is altijd in NL, zowel input als output."
            )
            combined_prompt = f"{department_prompts.get(department, '')}\n\n{basic_prompt}\n\n{text}"
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

if department in department_questions:
    st.subheader("Vragen om in je input te overwegen:")
    for question in department_questions[department]:
        st.text(f"- {question}")

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
