import streamlit as st
from speechmatics.models import ConnectionSettings
from speechmatics.batch_client import BatchClient
from httpx import HTTPStatusError
import os
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from langchain_core.output_parsers import StrOutputParser


# Initialize session state for 'page' and 'sub_department'
if 'page' not in st.session_state:
    st.session_state['page'] = 1
if 'sub_department' not in st.session_state:
    st.session_state['sub_department'] = None

# Dictionary for department-specific summary templates
department_templates = {
    "Schadebehandelaar": "Jij bent een expert in het samenvatten van gesprekken over schadeclaims. Focus op de details van de claim, de reactie van de medewerker, en de vervolgstappen.",
    "Particulieren": "Jij bent gespecialiseerd in het samenvatten van gesprekken met particuliere klanten. Leg de nadruk op klantvragen, aangeboden oplossingen en persoonlijke aandachtspunten.",
    "Bedrijven": "Als expert in bedrijfsgerelateerde gesprekken, vat samen wat de zakelijke behoeften zijn, welke oplossingen zijn geboden en wat de zakelijke actiepunten zijn.",
    "Financiële Planning": {
        "Pensioen": "Samenvatting gericht op pensioengerelateerde gesprekken. Benadruk pensioenplannen, klantvragen en advies.",
        "Collectief": "Focus op collectieve financiële planning, inclusief groepsvoordelen en -regelingen.",
        "Inkomen": "Richt je op gesprekken over inkomensplanning en -beheer, inclusief advies en actiepunten.",
        "Planning": "Benadruk de belangrijkste punten in financiële planning, toekomstige doelen en strategieën.",
        "Hypotheek": "Vat gesprekken samen over hypotheekgerelateerde onderwerpen, inclusief advies en klantopties."
    }
    # Voeg hier indien nodig meer afdelingen toe
}

# Function to generate the summary
def generate_response(txt, speaker1, speaker2, subject, department, sub_department, openai_api_key):
    department_prompt = department_templates.get(department, "Algemene samenvattingsinstructies")
    if isinstance(department_prompt, dict):  # For departments with subcategories
        department_prompt = department_prompt.get(sub_department, "Algemene samenvattingsinstructies voor subafdeling")

    full_prompt = f"{department_prompt}\n\nTranscript: {txt}\nSpreker 1: {speaker1}\nSpreker 2: {speaker2}\nOnderwerp: {subject}\n\nSamenvatting:"

    prompt_template = ChatPromptTemplate.from_template(full_prompt)

    model = ChatOpenAI(api_key=openai_api_key, model_name="gpt-4-0613", temperature=0.1)
    chain = prompt_template | model | StrOutputParser()

    summary = chain.invoke({"transcript": txt, "speaker1": speaker1, "speaker2": speaker2, "subject": subject})
    return summary

# Add a department selection page
def department_selection_page():
    st.title('Kies uw afdeling')
    department = st.selectbox("Selecteer de afdeling:", list(department_templates.keys()))
    sub_department = None
    if department == "Financiële Planning":
        sub_department = st.selectbox("Selecteer de subafdeling:", list(department_templates[department].keys()))
    if st.button("Ga door naar transcriptie"):
        st.session_state['department'] = department
        st.session_state['sub_department'] = sub_department
        st.session_state['page'] = 2

# Update Page 1: File Upload
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
        if st.button("Selecteer afdeling", key="continue_to_department"):
            st.session_state['page'] = 1.5

# Page 2: Transcription and Editing
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
                    st.error(f"Error during transcription: {str(e)}")
                    return
            os.remove(temp_path)
        if 'transcript' in st.session_state:
            edited_text = st.text_area("Edit Transcript", st.session_state['transcript'], height=300)
            speaker1 = st.text_input("Name for Speaker 1 (S1)")
            speaker2 = st.text_input("Name for Speaker 2 (S2)")
            subject = st.text_input("Subject of the Call")
            if st.button('Continue to Summary', key='continue_to_summary'):
                st.session_state['edited_text'] = edited_text
                st.session_state['speaker1'] = speaker1
                st.session_state['speaker2'] = speaker2
                st.session_state['subject'] = subject
                st.session_state['page'] = 3

# Update summary_page to include department
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

# Update Page Navigation
if st.session_state['page'] == 1:
    upload_page()
elif st.session_state['page'] == 1.5:
    department_selection_page()
elif st.session_state['page'] == 2:
    transcription_page()
elif st.session_state['page'] == 3:
    summary_page()