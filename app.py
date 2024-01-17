import streamlit as st
from speechmatics.models import ConnectionSettings
from speechmatics.batch_client import BatchClient
from httpx import HTTPStatusError
import os
from langchain.chains.summarize import load_summarize_chain
from langchain_openai import ChatOpenAI
from langchain.docstore.document import Document
from langchain.text_splitter import CharacterTextSplitter

# Function to generate response for summarization
def generate_response(txt, speaker1, speaker2, subject, openai_api_key):
    prompt_template = f"Samenvatting van een telefoongesprek over {subject}:\nBelangrijke punten:\n- \nActiepunten:\n- \nSamenvatting:\n"
    llm = ChatOpenAI(api_key=openai_api_key, model_name="gpt-3.5-turbo-1106")
    text_splitter = CharacterTextSplitter()
    texts = text_splitter.split_text(txt)
    docs = [Document(page_content=prompt_template + t) for t in texts]
    chain = load_summarize_chain(llm, chain_type='map_reduce')
    try:
        output = chain.run(docs)
        summary_text = output.get('output_text', '')
        return post_process_summary(summary_text, speaker1, speaker2, subject)
    except Exception as e:
        return f"Error during summarization: {str(e)}"

def post_process_summary(summary_text, speaker1, speaker2, subject):
    processed_summary = summary_text.replace('Speaker 1', speaker1).replace('Speaker 2', speaker2)
    action_points = "Geen"
    structured_summary = f"Onderwerp: {subject}\nWerknemer: {speaker1}\nGesprekspartner: {speaker2}\n{processed_summary}\nActiepunten: {action_points}"
    return structured_summary

# Page 1: File Upload
def upload_page():
    st.title('Speech to Text Transcription')
    uploaded_file = st.file_uploader("Choose an MP3 file", type="mp3")
    if uploaded_file is not None:
        st.session_state['uploaded_file'] = uploaded_file
        st.session_state['page'] = 2

# Page 2: Transcription and Editing
def transcription_page():
    st.title("Transcription and Editing")
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
            job_id = speech_client.submit_job(audio=temp_path, transcription_config=conf)
            transcript = speech_client.wait_for_completion(job_id, transcription_format="txt")
        except HTTPStatusError as e:
            st.error("Error during transcription: " + str(e))
            return
    os.remove(temp_path)
    edited_text = st.text_area("Edit Transcript", transcript, height=300)
    if st.button('Continue to Summary', key='continue_to_summary'):
        st.session_state['edited_text'] = edited_text
        st.session_state['page'] = 3

# Page 3: Summary
def summary_page():
    st.title("Summary of the Call")
    speaker1 = st.text_input("Name for Speaker 1 (S1)")
    speaker2 = st.text_input("Name for Speaker 2 (S2)")
    subject = st.text_input("Subject of the Call")
    if st.button('Generate Summary', key='generate_summary'):
        summary = generate_response(st.session_state['edited_text'], speaker1, speaker2, subject, st.secrets["openai"]["api_key"])
        st.text_area("Summary", summary, height=150)

if 'page' not in st.session_state:
    st.session_state['page'] = 1
if 'uploaded_file' not in st.session_state:
    st.session_state['uploaded_file'] = None

if st.session_state['page'] == 1:
    upload_page()
elif st.session_state['page'] == 2:
    transcription_page()
elif st.session_state['page'] == 3:
    summary_page()


