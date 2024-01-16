import streamlit as st
import openai  # Import OpenAI's library
from openai import OpenAI
from speechmatics.models import ConnectionSettings
from speechmatics.batch_client import BatchClient
from httpx import HTTPStatusError 
import os

client = OpenAI(api_key=st.secrets["openai"]["api_key"])


# Function to summarize text using GPT-3.5
def summarize_text(text):
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Samenvat de volgende Nederlandse tekst kort samen: " + text}
        ]
    )
    return response['choices'][0]['message']['content']

# Button to trigger summarization
if st.button('Summarize Transcript'):
    if st.session_state['transcript']:
        summary = summarize_text(st.session_state['transcript'])
        st.session_state['summary'] = summary
        st.text_area("Summary", summary, height=150)
    else:
        st.warning("Please transcribe a file first before summarizing.")

# Streamlit interface
st.title('Speech to Text Transcription')
uploaded_file = st.file_uploader("Choose an MP3 file", type="mp3")

# Initialize or reset the transcript in session state
if 'transcript' not in st.session_state or st.button('Discard Changes'):
    st.session_state['transcript'] = ''

if uploaded_file is not None:
    # Create a temp directory if it doesn't exist
    temp_dir = "temp"
    os.makedirs(temp_dir, exist_ok=True)
    temp_path = os.path.join(temp_dir, uploaded_file.name)

    # Save the file to the temp directory
    with open(temp_path, "wb") as f:
        f.write(uploaded_file.getbuffer())

    if st.button('Transcribe'):
        # Speechmatics setup using secrets
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

        with BatchClient(settings) as client:
            try:
                job_id = client.submit_job(
                    audio=temp_path,
                    transcription_config=conf,
                )
                st.write(f"Job {job_id} submitted successfully, waiting for transcript")

                # Store the transcript in session state
                st.session_state['transcript'] = client.wait_for_completion(job_id, transcription_format="txt")

            except HTTPStatusError as e:
                st.error("Error during transcription: " + str(e))

            # Clean up temporary file
            os.remove(temp_path)

# Editable Text Area
if st.session_state['transcript']:
    edited_text = st.text_area("Edit Transcript", st.session_state['transcript'], height=300)
    
    if st.button('Save Edited Text'):
        st.session_state['saved_text'] = edited_text
        st.success("Text saved successfully!")
