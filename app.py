import streamlit as st
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from speechmatics.models import ConnectionSettings
from speechmatics.batch_client import BatchClient
from httpx import HTTPStatusError
import os
import re
import time

# Initialisation of session state variables
if 'page' not in st.session_state:
    st.session_state.page = 1
if 'sub_department' not in st.session_state:
    st.session_state.sub_department = None
if 'department' not in st.session_state:
    st.session_state.department = ''
if 'direct_text' not in st.session_state:
    st.session_state.direct_text = ''

def load_prompt(department):
    prompt_file_path = f'prompts/{department.lower()}.txt'
    try:
        with open(prompt_file_path, 'r', encoding='utf-8') as file:
            return file.read()
    except FileNotFoundError:
        return ""

def preprocess_text(text):
    text = text.strip()
    text = re.sub(r'\s+', ' ', text)
    return text

def split_text(text, max_length=2000):
    text = preprocess_text(text)
    if len(text) <= max_length:
        return [text]
    segments = []
    while text:
        segment = text[:max_length]
        last_space = segment.rfind(' ')
        if last_space != -1 and len(text) > max_length:
            segments.append(text[:last_space])
            text = text[last_space+1:]
        else:
            segments.append(text)
            break
    return segments

def generate_response(segment, department, openai_api_key):
    department_prompt = load_prompt(department)
    full_prompt = f"{department_prompt}\n\n{segment}"
    prompt_template = ChatPromptTemplate.from_template(full_prompt)
    model = ChatOpenAI(api_key=openai_api_key, model_name="gpt-4-turbo-preview", temperature=0.20)
    chain = prompt_template | model | StrOutputParser()
    return chain.invoke({"transcript": segment})

def summarize_text(text, department, openai_api_key):
    segments = split_text(text)
    summaries = []
    start_time = time.time()
    for i, segment in enumerate(segments, start=1):
        summary = generate_response(segment, department, openai_api_key)
        summaries.append(summary)
        elapsed_time = time.time() - start_time
        estimated_total_time = (elapsed_time / i) * len(segments)
        remaining_time = estimated_total_time - elapsed_time
        st.write(f"Chunk {i}/{len(segments)} processed. Estimated remaining time: {remaining_time:.2f} seconds.")
    st.write(f"Completed in {elapsed_time:.2f} seconds.")
    return " ".join(summaries)

def transcribe_audio(file_path, auth_token):
    LANGUAGE = "en-US"  # Adjust based on your requirements
    settings = ConnectionSettings(
        url="https://asr.api.speechmatics.com/v2",
        auth_token=auth_token,
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
    transcript = ""
    with BatchClient(settings) as speech_client:
        try:
            job_id = speech_client.submit_job(audio=file_path, transcription_config=conf)
            transcript = speech_client.wait_for_completion(job_id, transcription_format="txt")
        except HTTPStatusError as e:
            st.error(f"Error during transcription: {str(e)}")
    return transcript

def upload_or_text_page():
    st.title('VA Gesprekssamenvatter')
    uploaded_file = st.file_uploader("Kies een MP3-bestand", type="mp3")
    if uploaded_file is not None:
        temp_dir = "temp"
        os.makedirs(temp_dir, exist_ok=True)
        temp_path = os.path.join(temp_dir, uploaded_file.name)
        with open(temp_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        transcript = transcribe_audio(temp_path, st.secrets["speechmatics"]["auth_token"])
        st.session_state.direct_text = transcript
        st.session_state.page = 1.5  # Proceed to department selection
    elif st.button("Plak tekst"):
        st.session_state.page = 4

def department_selection_page():
    st.title('Kies uw afdeling')
    department = st.selectbox("Selecteer de afdeling:", ["Schadebehandelaar", "Particulieren", "Bedrijven", "Financiële Planning"], index=0)
    st.session_state.department = department
    if department == "Financiële Planning":
        st.session_state.sub_department = st.selectbox("Selecteer de subafdeling:", ["Pensioen", "Collectief", "Inkomen", "Planning", "Hypotheek"], index=0)
    if st.button("Ga verder"):
        st.session_state.page = 3

def text_input_page():
    st.title("Tekst voor Samenvatting")
    direct_text = st.text_area("Plak de tekst hier", '', height=300)
    if st.button('Verzend tekst'):
        st.session_state.direct_text = direct_text
        st.session_state.page = 3

def summary_page():
    st.title("Samenvatting van het Gesprek")
    if st.session_state.direct_text:
        final_summary = summarize_text(
            st.session_state.direct_text,
            st.session_state.department,
            st.secrets["openai"]["api_key"]
        )
        st.text_area("Samenvatting", final_summary, height=150)
    else:
        st.write("Geen tekst gevonden om te verwerken.")

# Page navigation
if st.session_state.page == 1:
    upload_or_text_page()
elif st.session_state.page == 4:
    text_input_page()
elif st.session_state.page == 1.5:
    department_selection_page()
elif st.session_state.page == 3:
    summary_page()
