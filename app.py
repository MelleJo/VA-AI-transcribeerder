import streamlit as st
from speechmatics.models import ConnectionSettings
from speechmatics.batch_client import BatchClient
from httpx import HTTPStatusError
import os
from langchain.chains.summarize import load_summarize_chain
from langchain_openai import ChatOpenAI
from langchain.docstore.document import Document
from langchain.text_splitter import CharacterTextSplitter

# Functie voor het genereren van de samenvatting
def generate_response(txt, speaker1, speaker2, subject, openai_api_key):
    # Verbeterde template met nadrukkelijke instructie voor samenvatting in Nederlands
    prompt_template = (
        "taal = nl (Nederlands)"
        "Belangrijk: Genereer de samenvatting uitsluitend in het Nederlands. "
        "Als expert in het samenvatten van Nederlandse telefoongesprekken, "
        f"geef een nauwkeurige en beknopte samenvatting van het volgende gesprek over '{subject}'. "
        f"Deelnemers: Werknemer ('{speaker1}') en Gesprekspartner ('{speaker2}').\n\n"
        f"Transcript:\n{txt}\n\n"
        "Samenvatting:"
    )

    # Initialiseer het OpenAI-model
    llm = ChatOpenAI(api_key=openai_api_key, model_name="gpt-3.5-turbo-1106")

    try:
        response = llm(prompt_template)

        # Controleer of de respons de verwachte structuur heeft
        if hasattr(response, 'choices') and response.choices:
            summary_text = response.choices[0].text.strip()
        else:
            summary_text = "Samenvatting niet beschikbaar"

        return summary_text
    except Exception as e:
        st.error(f"Fout tijdens samenvatten: {str(e)}")
        return "Error during summarization"


# Page 1: File Upload
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
            st.session_state['page'] = 2


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

# Page 3: Summary
def summary_page():
    st.title("Samenvatting van het gesprek")
    if 'edited_text' in st.session_state and 'speaker1' in st.session_state and 'speaker2' in st.session_state and 'subject' in st.session_state:
        summary = generate_response(st.session_state['edited_text'], st.session_state['speaker1'], st.session_state['speaker2'], st.session_state['subject'], st.secrets["openai"]["api_key"])
        st.text_area("Samenvatting", summary, height=150)

# Initialize session state variables
if 'page' not in st.session_state:
    st.session_state['page'] = 1
if 'uploaded_file' not in st.session_state:
    st.session_state['uploaded_file'] = None

# Page Navigation
if st.session_state['page'] == 1:
    upload_page()
elif st.session_state['page'] == 2:
    transcription_page()
elif st.session_state['page'] == 3:
    summary_page()

