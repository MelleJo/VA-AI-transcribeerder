import streamlit as st
from speechmatics.models import ConnectionSettings
from speechmatics.batch_client import BatchClient
from httpx import HTTPStatusError
import os
from langchain.chains.summarize import load_summarize_chain
from langchain_openai import ChatOpenAI
from langchain.docstore.document import Document
from langchain.text_splitter import CharacterTextSplitter

# Page 1: File Upload
def upload_page():
    st.title('Speech to Text Transcription')
    uploaded_file = st.file_uploader("Choose an MP3 file", type="mp3")
    if uploaded_file is not None:
        st.session_state['uploaded_file'] = uploaded_file
        st.session_state['page'] = 2

if 'page' not in st.session_state:
    st.session_state['page'] = 1
if 'uploaded_file' not in st.session_state:
    st.session_state['uploaded_file'] = None

if st.session_state['page'] == 1:
    upload_page()

# Page 2: Transcription and Editing
def transcription_page():
    # ... (include the entire transcription_page function code here)

# Page 2: Transcription and Editing
def transcription_page():
    st.title("Transcription and Editing")
    
    # Check if an uploaded file is available
    if 'uploaded_file' in st.session_state and st.session_state['uploaded_file'] is not None:
        # Process the uploaded file
        temp_dir = "temp"
        os.makedirs(temp_dir, exist_ok=True)
        temp_path = os.path.join(temp_dir, st.session_state['uploaded_file'].name)
        with open(temp_path, "wb") as f:
            f.write(st.session_state['uploaded_file'].getbuffer())

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
                job_id = speech_client.submit_job(
                    audio=temp_path,
                    transcription_config=conf,
                )
                transcript = speech_client.wait_for_completion(job_id, transcription_format="txt")
            except HTTPStatusError as e:
                st.error("Error during transcription: " + str(e))
                return

        os.remove(temp_path)
        
        # Show editable transcription
        edited_text = st.text_area("Edit Transcript", transcript, height=300)
        speaker1 = st.text_input("Name for Speaker 1 (S1)")
        speaker2 = st.text_input("Name for Speaker 2 (S2)")
        subject = st.text_input("Subject of the Call")

        if st.button('Continue to Summary', key='continue_to_summary'):
            # Save the edited transcript and other details to the session state
            st.session_state['edited_text'] = edited_text
            st.session_state['speaker1'] = speaker1
            st.session_state['speaker2'] = speaker2
            st.session_state['subject'] = subject
            st.session_state['page'] = 3  # Move to summary page
    else:
        st.error("Please upload a file on the previous page.")

if st.session_state['page'] == 2:
    transcription_page()


