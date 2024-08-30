# src/utils.py

import os
from src.config import PROMPTS_DIR, AUDIO_MODEL, SUMMARY_MODEL, MAX_TOKENS, TEMPERATURE, AUDIO_SEGMENT_LENGTH
import streamlit as st
from PyPDF2 import PdfReader
from docx import Document
from openai import OpenAI
from pydub import AudioSegment
import tempfile

client = OpenAI(api_key=config.OPENAI_API_KEY)

def load_prompts_and_departments():
    prompts = {}
    for department in os.listdir(PROMPTS_DIR):
        department_path = os.path.join(PROMPTS_DIR, department)
        if os.path.isdir(department_path):
            prompts[department] = {}
            for prompt_file in os.listdir(department_path):
                if prompt_file.endswith('.txt'):
                    prompt_name = os.path.splitext(prompt_file)[0]
                    with open(os.path.join(department_path, prompt_file), 'r') as f:
                        prompts[department][prompt_name] = f.read()
    return prompts

def get_departments():
    return list(load_prompts_and_departments().keys())

def get_prompts(department):
    return load_prompts_and_departments().get(department, {})

def split_audio(file):
    audio = AudioSegment.from_file(file)
    chunks = []
    for i in range(0, len(audio), AUDIO_SEGMENT_LENGTH):
        chunks.append(audio[i:i+AUDIO_SEGMENT_LENGTH])
    return chunks

def transcribe_audio(audio_file):
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as temp_audio:
            temp_audio.write(audio_file.read())
            temp_audio_path = temp_audio.name

        audio_segments = split_audio(temp_audio_path)
        full_transcript = ""

        for i, segment in enumerate(audio_segments):
            with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as temp_segment:
                segment.export(temp_segment.name, format="wav")
                with open(temp_segment.name, "rb") as audio_segment:
                    transcript = client.audio.transcriptions.create(
                        model=AUDIO_MODEL,
                        file=audio_segment,
                        response_format="text"
                    )
                full_transcript += transcript + " "
            os.unlink(temp_segment.name)
            st.progress((i + 1) / len(audio_segments))

        os.unlink(temp_audio_path)
        return full_transcript.strip()
    except Exception as e:
        st.error(f"An error occurred during audio transcription: {str(e)}")
        return None

def process_text_file(file):
    try:
        if file.name.endswith('.pdf'):
            pdf_reader = PdfReader(file)
            text = ""
            for page in pdf_reader.pages:
                text += page.extract_text()
        elif file.name.endswith('.docx'):
            doc = Document(file)
            text = "\n".join([paragraph.text for paragraph in doc.paragraphs])
        else:
            text = file.getvalue().decode("utf-8")
        return text
    except Exception as e:
        st.error(f"An error occurred while processing the file: {str(e)}")
        return None