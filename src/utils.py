# src/utils.py

import os
from src.config import PROMPTS_DIR, AUDIO_MODEL, SUMMARY_MODEL, MAX_TOKENS, TEMPERATURE, AUDIO_SEGMENT_LENGTH, OPENAI_API_KEY
import streamlit as st
from PyPDF2 import PdfReader
from docx import Document
from openai import OpenAI
from pydub import AudioSegment
import tempfile

client = OpenAI(api_key=OPENAI_API_KEY)

def load_prompts():
    prompts = {}
    for prompt_file in os.listdir(PROMPTS_DIR):
        if prompt_file.endswith('.txt'):
            prompt_name = os.path.splitext(prompt_file)[0]
            with open(os.path.join(PROMPTS_DIR, prompt_file), 'r') as f:
                prompts[prompt_name] = f.read()
    return prompts

def get_prompt_names():
    return list(load_prompts().keys())

def get_prompt_content(prompt_name):
    return load_prompts().get(prompt_name, "")

def split_audio(file):
    audio = AudioSegment.from_file(file)
    chunks = []
    for i in range(0, len(audio), AUDIO_SEGMENT_LENGTH):
        chunks.append(audio[i:i+AUDIO_SEGMENT_LENGTH])
    return chunks


def transcribe_audio(audio_file, progress_callback=None):
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as temp_audio:
            temp_audio.write(audio_file.read())
            temp_audio_path = temp_audio.name

        audio = AudioSegment.from_wav(temp_audio_path)
        total_duration = len(audio)
        chunk_duration = AUDIO_SEGMENT_LENGTH
        chunks = [audio[i:i+chunk_duration] for i in range(0, total_duration, chunk_duration)]

        full_transcript = ""

        for i, chunk in enumerate(chunks):
            with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as temp_chunk:
                chunk.export(temp_chunk.name, format="wav")
                with open(temp_chunk.name, "rb") as audio_chunk:
                    transcript = client.audio.transcriptions.create(
                        model=AUDIO_MODEL,
                        file=audio_chunk,
                        response_format="text"
                    )
                full_transcript += transcript + " "
            os.unlink(temp_chunk.name)
            
            if progress_callback:
                progress_callback(i + 1, len(chunks))

        os.unlink(temp_audio_path)
        return full_transcript.strip()
    except Exception as e:
        st.error(f"Er is een fout opgetreden tijdens de audiotranscriptie: {str(e)}")
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