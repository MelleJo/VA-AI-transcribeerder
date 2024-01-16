import streamlit as st
from langchain.chains.summarize import load_summarize_chain
from langchain_openai import ChatOpenAI
from langchain.docstore.document import Document
from langchain.text_splitter import CharacterTextSplitter
from speechmatics.models import ConnectionSettings
from speechmatics.batch_client import BatchClient
from httpx import HTTPStatusError 
import os

# Function to generate response for summarization
def generate_response(txt, speaker1, speaker2, subject, openai_api_key):
    # Custom prompt template for structured summary in Dutch
    prompt_template = (
        f"Samenvatting van een telefoongesprek:\n"
        f"Onderwerp: {subject}\n"
        "Belangrijke punten:\n{key_points}\n"
        "Actiepunten:\n{action_items}\n"
        "Samenvatting:\n"
    )

    llm = ChatOpenAI(api_key=openai_api_key, model_name="gpt-3.5-turbo-1106")
    text_splitter = CharacterTextSplitter()
    texts = text_splitter.split_text(txt)

    docs = [Document(page_content=prompt_template.format(key_points="", action_items="") + t) for t in texts]
    chain = load_summarize_chain(llm, chain_type='map_reduce')

    output = chain.invoke(docs)
    return post_process_summary(output, speaker1, speaker2)

def post_process_summary(summary, speaker1, speaker2):
    # Example processing - this needs to be adjusted based on real data
    processed_summary = summary.replace(speaker1, 'Werknemer').replace(speaker2, 'Klant/Collega')
    
    # Extract action points - example pattern, adjust as needed
    action_points = "Geen"  # Default if no action points are detected
    if "actie" in processed_summary.lower():
        action_points = "Some extracted action points"  # Replace with actual extraction logic

    # Structure the summary
    structured_summary = f"Samenvatting:\n{processed_summary}\nActiepunten: {action_points}"

    return structured_summary




# Streamlit interface
st.title('Speech to Text Transcription')
speaker1 = st.text_input("Name of Speaker 1 (S1)", "User")
speaker2 = st.text_input("Name of Speaker 2 (S2)", "Client")
subject = st.text_input("Subject of the Call", "Adviesgesprek")
uploaded_file = st.file_uploader("Choose an MP3 file", type="mp3")

if 'transcript' not in st.session_state or st.button('Discard Changes'):
    st.session_state['transcript'] = ''

if uploaded_file is not None:
    temp_dir = "temp"
    os.makedirs(temp_dir, exist_ok=True)
    temp_path = os.path.join(temp_dir, uploaded_file.name)
    with open(temp_path, "wb") as f:
        f.write(uploaded_file.getbuffer())

    if st.button('Transcribe'):
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
                st.session_state['transcript'] = speech_client.wait_for_completion(job_id, transcription_format="txt")
            except HTTPStatusError as e:
                st.error("Error during transcription: " + str(e))
            os.remove(temp_path)

# Editable Text Area
edited_text = st.text_area("Edit Transcript", st.session_state.get('transcript', ''), height=300)


# Button to trigger summarization
if st.button('Summarize Transcript'):
    if edited_text:
        summary = generate_response(edited_text, speaker1, speaker2, subject, st.secrets["openai"]["api_key"])
        st.session_state['summary'] = summary
        st.text_area("Summary", summary, height=150)
    else:
        st.warning("Please transcribe a file first before summarizing.")


# Display saved edited text
if 'saved_text' in st.session_state:
    st.text_area("Saved Edited Text", st.session_state['saved_text'], height=300)

if st.button('Save Edited Text'):
    st.session_state['saved_text'] = edited_text
    st.success("Text saved successfully!")
