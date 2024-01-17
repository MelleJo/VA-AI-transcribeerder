import streamlit as st
from speechmatics.models import ConnectionSettings
from speechmatics.batch_client import BatchClient
from httpx import HTTPStatusError
import os
from langchain.chains.summarize import load_summarize_chain
from langchain_openai import ChatOpenAI
from langchain.docstore.document import Document
from langchain.text_splitter import CharacterTextSplitter

# Navigation function
def go_to_page(page_number):
    st.session_state['page'] = page_number


# Navigation bar
st.sidebar.title("Navigation")
if st.sidebar.button("Upload", key="nav_upload"):
    go_to_page(1)
if st.sidebar.button("Transcription", key="nav_transcription"):
    go_to_page(2)
if st.sidebar.button("Summary", key="nav_summary"):
    go_to_page(3)



# Navigation 
def go_to_page(page_number):
    st.session_state['page'] = page_number

def next_page():
    st.session_state['page'] += 1

def previous_page():
    st.session_state['page'] -= 1



# Function to safely delete a file
def safe_file_delete(file_path):
    if file_path and isinstance(file_path, (str, bytes, os.PathLike)) and os.path.exists(file_path):
        try:
            os.remove(file_path)
        except OSError:
            pass


# Function to generate response for summarization
def generate_response(txt, speaker1, speaker2, subject, openai_api_key):
    # Template with clear instructions for summarization in Dutch
    prompt_template = (
        "Samenvat dit telefoongesprek in het Nederlands. Het gesprek gaat over: '{}'.\n"
        "Deelnemers zijn: Werknemer ('{}') en Gesprekspartner ('{}').\n"
        "Telefoongesprek Transcript:\n{}\n"
        "Samenvatting:\n".format(subject, speaker1, speaker2, txt)
    )

    # Initialize the OpenAI model
    llm = ChatOpenAI(api_key=openai_api_key, model_name="gpt-3.5-turbo-1106")

    try:
        response = llm(prompt_template)
        
        # Check if response is structured correctly
        if response and hasattr(response, 'choices') and response.choices:
            summary_text = response.choices[0].text.strip()
        else:
            st.warning("API response structure is unexpected.")
            return "Samenvatting niet beschikbaar"

        if not summary_text:
            st.warning("Summary text is empty.")
            return "Samenvatting niet beschikbaar"

        return summary_text

    except Exception as e:
        st.error(f"Fout tijdens samenvatten: {str(e)}")
        return "Fout tijdens samenvatten: Kan geen samenvatting genereren"









def post_process_summary(summary_text, speaker1, speaker2, subject):
    structured_summary = (
        f"Onderwerp: {subject}\n"
        f"Werknemer: {speaker1}\n"
        f"Gesprekspartner: {speaker2}\n"
        f"{summary_text}\n"
        "Actiepunten: Geen"
    )
    return structured_summary





# Page 1: File Upload
def upload_page():
    st.title('Speech to Text Transcription')
    uploaded_file = st.file_uploader("Choose an MP3 file", type="mp3")
    if uploaded_file is not None:
        # Delete the previous file if it exists
        if 'last_uploaded_file' in st.session_state:
            safe_file_delete(st.session_state['last_uploaded_file'])

        # Process the new file
        temp_dir = "temp"
        os.makedirs(temp_dir, exist_ok=True)
        temp_path = os.path.join(temp_dir, uploaded_file.name)
        
        with open(temp_path, "wb") as f:
            f.write(uploaded_file.getbuffer())

        # Update session state
        st.session_state['last_uploaded_file'] = temp_path
        st.session_state['uploaded_file'] = uploaded_file
        st.session_state['page'] = 2
        
        # Add a Continue button
        if st.button("Continue", key="continue_from_upload"):
            next_page()

# Page 2: Transcription and Editing
def transcription_page():
    st.title("Transcription and Editing")
    
    if 'uploaded_file' in st.session_state and st.session_state['uploaded_file'] is not None:
        temp_dir = "temp"
        os.makedirs(temp_dir, exist_ok=True)
        temp_path = os.path.join(temp_dir, st.session_state['uploaded_file'].name)
        
        # Transcribe button
        if st.button('Transcribe Audio', key='transcribe_audio'):
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
                    st.session_state['transcript'] = speech_client.wait_for_completion(job_id, transcription_format="txt")
                except HTTPStatusError as e:
                    st.error("Error during transcription: " + str(e))
                    return

            safe_file_delete(temp_path)

        # Check if transcription is done
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
                st.experimental_rerun()
    else:
        st.error("Please upload a file on the previous page.")

# Page 3: Summary
def summary_page():
    st.title("Summary of the Call")
    if 'edited_text' in st.session_state and 'speaker1' in st.session_state and 'speaker2' in st.session_state and 'subject' in st.session_state:
        summary = generate_response(st.session_state['edited_text'], st.session_state['speaker1'], st.session_state['speaker2'], st.session_state['subject'], st.secrets["openai"]["api_key"])
        st.text_area("Summary", summary, height=150)
    else:
        st.error("Please complete the transcription and editing steps first.")

# Initialize session state variables
if 'page' not in st.session_state:
    st.session_state['page'] = 1
if 'uploaded_file' not in st.session_state:
    st.session_state['uploaded_file'] = None
if 'last_uploaded_file' not in st.session_state:
    st.session_state['last_uploaded_file'] = None

# Page Navigation
if st.session_state['page'] == 1:
    upload_page()
elif st.session_state['page'] == 2:
    transcription_page()
elif st.session_state['page'] == 3:
    summary_page()

