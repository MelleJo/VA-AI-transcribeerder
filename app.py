import streamlit as st
from speechmatics.models import ConnectionSettings
from speechmatics.batch_client import BatchClient
from httpx import HTTPStatusError 
import os

# Streamlit interface
st.title('Speech to Text Transcription')
uploaded_file = st.file_uploader("Choose an MP3 file", type="mp3")
if uploaded_file is not None:
    # Save the file to a temporary directory
    temp_path = os.path.join("temp", uploaded_file.name)
    with open(temp_path, "wb") as f:
        f.write(uploaded_file.getbuffer())

    if st.button('Transcribe'):
        # Speechmatics setup using secrets
        AUTH_TOKEN = st.secrets["speechmatics"]["auth_token"]
        LANGUAGE = "en"

        settings = ConnectionSettings(
            url="https://asr.api.speechmatics.com/v2",
            auth_token=AUTH_TOKEN,
        )

        conf = {
            "type": "transcription",
            "transcription_config": {
                "language": LANGUAGE,
                "enable_entities": True,
            },
        }

        with BatchClient(settings) as client:
            try:
                job_id = client.submit_job(
                    audio=temp_path,
                    transcription_config=conf,
                )
                st.write(f"Job {job_id} submitted successfully, waiting for transcript")

                transcript = client.wait_for_completion(job_id, transcription_format="txt")
                st.text_area("Transcript", transcript, height=300)
            except HTTPStatusError as e:
                st.error("Error during transcription: " + str(e))

            # Clean up temporary file
            os.remove(temp_path)
