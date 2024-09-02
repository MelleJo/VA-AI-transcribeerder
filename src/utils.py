import os
from src.config import PROMPTS_DIR, AUDIO_MODEL, SUMMARY_MODEL, MAX_TOKENS, TEMPERATURE, AUDIO_SEGMENT_LENGTH, OPENAI_API_KEY
import streamlit as st
from PyPDF2 import PdfReader
from docx import Document
from openai import OpenAI
from pydub import AudioSegment
import tempfile
import io
import json

client = OpenAI(api_key=OPENAI_API_KEY)

def load_prompts():
    prompts = {}
    base_prompt_path = os.path.join(PROMPTS_DIR, 'base_prompt.txt')
    with open(base_prompt_path, 'r') as f:
        base_prompt = f.read()

    for filename in os.listdir(PROMPTS_DIR):
        if filename.endswith('.txt') and filename != 'base_prompt.txt':
            prompt_name = os.path.splitext(filename)[0]
            with open(os.path.join(PROMPTS_DIR, filename), 'r') as f:
                task_specific_prompt = f.read()
            full_prompt = base_prompt.replace('[TASK_SPECIFIC_INSTRUCTIONS]', task_specific_prompt)
            full_prompt = full_prompt.replace('[PROMPT_NAME]', prompt_name)
            prompts[prompt_name] = full_prompt

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
        audio = AudioSegment.from_file(audio_file)
        chunks = split_audio(audio_file)
        total_chunks = len(chunks)
        full_transcript = ""

        for i, chunk in enumerate(chunks):
            with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as temp_chunk:
                chunk.export(temp_chunk.name, format="wav")
                with open(temp_chunk.name, "rb") as audio_chunk:
                    try:
                        response = client.audio.transcriptions.create(
                            model=AUDIO_MODEL,
                            file=audio_chunk,
                            response_format="text"
                        )
                        transcript = response
                    except json.JSONDecodeError:
                        st.warning(f"Er was een probleem bij het decoderen van het antwoord voor chunk {i+1}. Overslaan en doorgaan.")
                        continue
                full_transcript += transcript + " "
            os.unlink(temp_chunk.name)

            if progress_callback:
                progress_callback(i + 1, total_chunks)

        return full_transcript.strip()
    except Exception as e:
        raise Exception(f"An error occurred during audio transcription: {str(e)}")

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

def process_audio_input(audio_data):
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as temp_audio:
            temp_audio.write(audio_data['bytes'])
            audio_file_path = temp_audio.name
        return audio_file_path
    except Exception as e:
        st.error(f"An error occurred while processing the audio input: {str(e)}")
        return None