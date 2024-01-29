import streamlit as st
from speechmatics.models import ConnectionSettings
from speechmatics.batch_client import BatchClient
from httpx import HTTPStatusError
import os
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from langchain_core.output_parsers import StrOutputParser

# Initialisatie van pagina in session state
if 'page' not in st.session_state:
    st.session_state['page'] = 1
if 'sub_department' not in st.session_state:
    st.session_state['sub_department'] = None

# Functie om de prompt te laden
def load_prompt(department):
    prompt_file_path = f'prompts/{department.lower()}.txt'
    try:
        with open(prompt_file_path, 'r', encoding='utf-8') as file:
            return "prompt wel gevonden, jippie!"
    except FileNotFoundError:
        return "Standaard prompt als het bestand niet wordt gevonden."

# Functie om de samenvatting te genereren
def generate_response(txt, speaker1, speaker2, subject, department, sub_department, openai_api_key):
    department_prompt = load_prompt(department)
    full_prompt = f"{department_prompt}\n\n### Transcript Informatie:\n" + \
                  f"- **Transcript**: {txt}\n- **Spreker 1**: {speaker1}\n- **Spreker 2**: {speaker2}\n- **Onderwerp**: {subject}\n\n" + \
                  "### Samenvatting Gesprek:\n...\n\n### Actiepunten:\n...\n\n### Eind Samenvatting:"
    
    prompt_template = ChatPromptTemplate.from_template(full_prompt)
    model = ChatOpenAI(api_key=openai_api_key, model_name="gpt-4-turbo-preview", temperature=0.20)
    chain = prompt_template | model | StrOutputParser()
    summary = chain.invoke({"transcript": txt, "speaker1": speaker1, "speaker2": speaker2, "subject": subject})
    return summary

# Pagina voor het selecteren van de afdeling
def department_selection_page():
    st.title('Kies uw afdeling')
    department = st.selectbox("Selecteer de afdeling:", ["Schadebehandelaar", "Particulieren", "Bedrijven", "Financiële Planning"])
    sub_department = None
    if department == "Financiële Planning":
        sub_department = st.selectbox("Selecteer de subafdeling:", ["Pensioen", "Collectief", "Inkomen", "Planning", "Hypotheek"])
    if st.button("Ga door naar transcriptie"):
        st.session_state['department'] = department
        st.session_state['sub_department'] = sub_department
        st.session_state['page'] = 2

# Pagina voor het uploaden van bestanden
def upload_page():
    st.title('VA gesprekssamenvatter')
    uploaded_file = st.file_uploader("Kies een MP3 bestand", type="mp3")
    if uploaded_file is not None:
        temp_dir = "temp"
        os.makedirs(temp_dir, exist_ok=True)
        temp_path = os.path.join(temp_dir, uploaded_file.name)
        with open(temp_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        st.session_state['uploaded_file'] = uploaded_file
        if st.button("Ga door naar de transcriptie", key="continue_to_transcription"):
            st.session_state['page'] = 1.5

# Pagina voor transcriptie en bewerking
def transcription_page():
    st.title("Transcriberen en bewerken")
    if 'uploaded_file' in st.session_state and st.session_state['uploaded_file'] is not None:
        temp_path = os.path.join("temp", st.session_state['uploaded_file'].name)
        if st.button('Transcriberen', key='transcribe_audio'):
            AUTH_TOKEN = st.secrets["speechmatics"]["auth_token"]
            LANGUAGE = "nl"
            settings = ConnectionSettings(
                url="https://asr.api.speechmatics.com/v2",
                auth_token=AUTH_TOKEN,
            )
            conf = {
                "type": "transcription",
                "transcription_config": {
                    "language": LANGUAGE,
                    "operating_point": "enhanced",
                    "diarization": "speaker",
                    "speaker_diarization_config": {
                        "speaker_sensitivity": 0.2
                    }
                },
            }
            with BatchClient(settings) as speech_client:
                try:
                    job_id = speech_client.submit_job(audio=temp_path, transcription_config=conf)
                    st.session_state['transcript'] = speech_client.wait_for_completion(job_id, transcription_format="txt")
                except HTTPStatusError as e:
                    st.error(f"Fout tijdens transcriberen: {str(e)}")
                    return
            os.remove(temp_path)

        if 'transcript' in st.session_state:
            edited_text = st.text_area("Bewerk Transcript", st.session_state['transcript'], height=300)
            speaker1 = st.text_input("Naam van Spreker 1 (S1)")
            speaker2 = st.text_input("Naam van Spreker 2 (S2)")
            subject = st.text_input("Onderwerp van het Gesprek")
            if st.button('Ga verder naar Samenvatting', key='continue_to_summary'):
                st.session_state['edited_text'] = edited_text
                st.session_state['speaker1'] = speaker1
                st.session_state['speaker2'] = speaker2
                st.session_state['subject'] = subject
                st.session_state['page'] = 3

# Pagina voor samenvatting
def summary_page():
    st.title("Samenvatting van het gesprek")
    if 'edited_text' in st.session_state and 'speaker1' in st.session_state and 'speaker2' in st.session_state and 'subject' in st.session_state and 'department' in st.session_state:
        summary = generate_response(
            st.session_state['edited_text'],
            st.session_state['speaker1'],
            st.session_state['speaker2'],
            st.session_state['subject'],
            st.session_state['department'],
            st.session_state['sub_department'],
            st.secrets["openai"]["api_key"]
        )
        st.text_area("Samenvatting", summary, height=150)

# Pagina navigatie
if st.session_state['page'] == 1:
    upload_page()
elif st.session_state['page'] == 1.5:
    department_selection_page()
elif st.session_state['page'] == 2:
    transcription_page()
elif st.session_state['page'] == 3:
    summary_page()
