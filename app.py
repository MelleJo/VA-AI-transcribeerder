import streamlit as st
import os
import re
import time
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from speechmatics.models import ConnectionSettings
from speechmatics.batch_client import BatchClient
from httpx import HTTPStatusError

# Initialize session state variables
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
        st.error(f"Prompt file for {department} not found.")
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
    if not department_prompt:
        st.error("Failed to load the department prompt. Using default summarization.")
        department_prompt = "Please summarize the following text:"
    full_prompt = f"{department_prompt}\n\n{segment}\n\n### Please provide a summary following the structure above."
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
        elapsed_minutes = elapsed_time / 60
        remaining_minutes = remaining_time / 60
        st.write(f"Chunk {i}/{len(segments)} processed. Estimated remaining time: {remaining_minutes:.2f} minutes.")
    total_duration = time.time() - start_time
    total_minutes = total_duration / 60
    st.write(f"Completed in {total_minutes:.2f} minutes.")
    return " ".join(summaries)

def upload_or_text_page():
    st.title('VA Gesprekssamenvatter')
    uploaded_file = st.file_uploader("Kies een MP3-bestand", type="mp3")
    if uploaded_file is not None:
        temp_dir = "temp"
        os.makedirs(temp_dir, exist_ok=True)
        temp_path = os.path.join(temp_dir, uploaded_file.name)
        with open(temp_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        st.session_state['direct_text'] = transcribe_audio(temp_path, st.secrets["speechmatics"]["auth_token"])
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
