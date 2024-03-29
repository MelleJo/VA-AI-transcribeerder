import streamlit as st
from speechmatics.models import ConnectionSettings
from speechmatics.batch_client import BatchClient
from httpx import HTTPStatusError
import os
from openai import OpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from langchain_core.output_parsers import StrOutputParser
from datetime import datetime

datum_transcript = datetime.now().strftime("%d-%m-%Y %H:%M:%S")

# Function to generate the summary

openai_api_key = st.secrets["openai"]["api_key"]

basic_prompt_rules = """"
Jij bent een expert in het maken van beknopte maar effectieve samenvattingen voor het dossier, jij hebt een perfecte afweging in wat belangrijk is voor een dossier en wat niet. Geef de samenvatting altijd in bulletpoints en niet in vol uitgeschreven zinnen. Gebruik duidelijke kopjes. De samenvatting is altijd in het Nederlands, het betreft altijd een telefoongesprek tussen twee partijen. Je zorgt altijd dat er geen belangrijke informatie wordt overgeslagen. Vermeld het onderwerp, en de sprekers. Als er informatie wordt gegeven zoals een bedrag, een postcode, of een datum, dan noteer je die altijd expliciet.
""""" 

department_prompts = {
    "schade": """"
    Jij bent een expert schadebehandelaar, je stelt alle relevante vragen die benodigd zijn voor het behandelen van een schade.
    Kopje 1: Details over het telefoon gesprek, {datum_transcript}, {speaker1}, {speaker2}, {subject}.
    Kopje 2: Korte samenvatting van het gesprek: hier gebruik je bulletpoints en leg je in zo min mogelijk tekst uit waar het gesprek over ging, en enige informatie die belangrijk is voor het dossier.
    Kopje 3: Schademelding:
    Als er een datum, postcode, of bedrag is gegeven, dan noteer je die altijd expliciet.
    Je zorgt ervoor dat alle informatie met betrekking tot een schade worden opgenomen. 
    Stel de volgende schade bij het samenstellen van de schademelding, mocht iets niet aan bod zijn gekomen, dan ga je er vanuit dat dit niet benodigd is, dus laat je dit weg uit de samenvatting.  
    1. Object van schade: Specificeer het beschadigde object. 
    2. Schadebedrag: Vermeld de hoogte van de schade in euro's. 
    3. Status van herstel en expertise: Is de schade hersteld? Is er een expertbeoordeling geweest?
    4. Datum van incident: Noteer wanneer de schade is opgetreden.
    5. Onder welke polis zou deze schade kunnen vallen, beoordeel dit aan de hand van de soort schade als het niet is genoemd. 
    6. Documentatie: Zijn er foto's of andere bewijsstukken verstuurd? 
    7. Zichtbaarheid van schade: Is de schade vanaf de straat zichtbaar of is het meer verborgen?

    Kopje 4: Actiepunten schadebehandelaar/collega: Analyseer in het transcript of er actiepunten zijn voor de schadebehandelaar.
    Kopje 5: Actiepunten klant: Analyseer in het transcript of er actiepunten zijn voor de klant.

    Je houdt de samenvatting zelf kort en beperkt tot de belangrijkste details voor de context van de schade(behandeling), maar zorg er voor (dit is de grootste prioriteit) dat geen enkele gegevens met betrekking tot de schade zelf worden weggelaten. 
    Maak simpele directe zinnen. 
    """,
    "financiele planning": "Samenvatting voor de afdeling Financiële Planning: ...",
    "adviseurs": "Samenvatting voor de afdeling Adviseurs: ...",
    "bedrijven": "Samenvatting voor de afdeling Bedrijven: ...",
    "particulieren": "Samenvatting voor de afdeling Particulieren: ...",
    "algemeen": "Algemene samenvatting: ..."
}

def generate_response(txt, speaker1, speaker2, subject, department, openai_api_key):
    department_prompt = department_prompts.get(department, "Algemene samenvatting: ...")
    detailed_instructions = f"{basic_prompt_rules} {department_prompt}"
    prompt_template = ChatPromptTemplate.from_template(
        f"Vat dit samen: {{transcript}} van {{speaker1}} en {{speaker2}} over {{subject}}. Met deze instructies: {detailed_instructions}"
    )
    model = ChatOpenAI(api_key=openai_api_key, model_name="gpt-4-0125-preview", temperature=0.1)
    chain = prompt_template | model | StrOutputParser()
    summary = chain.invoke({
        "transcript": txt,
        "speaker1": speaker1,
        "speaker2": speaker2,
        "subject": subject,
        "datum_transcript": datum_transcript  
        })
    return summary




#def transcribe_with_whisper(audio_path):
    client = OpenAI(api_key=openai_api_key)
    with open(audio_path, "rb") as audio_file:
        transcription = client.audio.transcriptions.create(
            model="whisper-1",
            file=audio_file,
            language="nl"
        )
    return transcription.text

st.title('Gesprekssamenvattertool - testversie 0.2.1.')

# Page 1: File Upload
uploaded_file = st.file_uploader("Kies een MP3 bestand", type="mp3")
if uploaded_file is not None:
    temp_dir = "temp"
    os.makedirs(temp_dir, exist_ok=True)
    temp_path = os.path.join(temp_dir, uploaded_file.name)
    with open(temp_path, "wb") as f:
        f.write(uploaded_file.getbuffer())
    st.session_state['uploaded_file'] = uploaded_file
    st.session_state['page'] = 2

if 'page' in st.session_state and st.session_state['page'] == 2:
    # Page 2: Transcription and Editing
    st.title("Transcriberen en bewerken")
    department = st.radio("Selecteer de afdeling", list(department_prompts.keys()))
    if 'uploaded_file' in st.session_state:
        temp_path = os.path.join("temp", st.session_state['uploaded_file'].name)

        if st.button('Transcriberen', key='transcribe_audio'):
            with st.spinner("Transcriptie wordt gegenereerd, dit kan even duren, afhankelijk van de lengte van het gesprek..."):
                #try:
                    #st.session_state['transcript'] = transcribe_with_whisper(temp_path)
                #except Exception as e:
                    #st.error(f"Error during transcription: {str(e)}")
                #os.remove(temp_path)


                # Speechmatics transcription logic here
                AUTH_TOKEN = st.secrets["speechmatics"]["auth_token"]
                LANGUAGE = "nl"
                settings = ConnectionSettings(url="https://asr.api.speechmatics.com/v2", auth_token=AUTH_TOKEN)
                conf = {"type": "transcription", "transcription_config": {"language": LANGUAGE, "operating_point": "enhanced", "diarization": "speaker", "speaker_diarization_config": {"speaker_sensitivity": 0.2}}}
                with BatchClient(settings) as speech_client:
                    try:
                        job_id = speech_client.submit_job(audio=temp_path, transcription_config=conf)
                        st.session_state['transcript'] = speech_client.wait_for_completion(job_id, transcription_format="txt")
                    except HTTPStatusError as e:
                        st.error(f"Error during transcription: {str(e)}")
                os.remove(temp_path)


        if 'transcript' in st.session_state:
            edited_text = st.text_area("Edit Transcript", st.session_state['transcript'], height=1000)
            speaker1 = st.text_input("Name for Speaker 1 (S1)")
            speaker2 = st.text_input("Name for Speaker 2 (S2)")
            subject = st.text_input("Subject of the Call")
            st.session_state['edited_text'] = edited_text
            st.session_state['speaker1'] = speaker1
            st.session_state['speaker2'] = speaker2
            st.session_state['subject'] = subject
            st.session_state['department'] = department
            st.session_state['page'] = 3

if 'page' in st.session_state and st.session_state['page'] == 3:
    # Page 3: Summary
    st.title("Samenvatting van het gesprek")
    if st.button('Genereer Samenvatting', key='generate_summary'):
        if 'edited_text' in st.session_state and 'speaker1' in st.session_state and 'speaker2' in st.session_state and 'subject' in st.session_state:
            with st.spinner("Samenvatting wordt gegenereerd, dit kan even duren afhankelijk van de lengte van het transcript..."):
                summary = generate_response(
                    st.session_state['edited_text'],
                    st.session_state['speaker1'],
                    st.session_state['speaker2'],
                    st.session_state['subject'],
                    st.session_state["department"],
                    st.secrets["openai"]["api_key"]
                )
                #summary = st.text_area("Samenvatting", summary, height=1000)
                st.markdown(summary)






