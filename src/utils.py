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
import moviepy.editor as mp

client = OpenAI(api_key=OPENAI_API_KEY)

def load_prompts():
    prompts = {}
    base_prompt_path = os.path.join(PROMPTS_DIR, 'base_prompt.txt')
    try:
        with open(base_prompt_path, 'r', encoding='utf-8') as f:
            prompts['base_prompt.txt'] = f.read()
    except FileNotFoundError:
        st.warning(f"Base prompt file not found: {base_prompt_path}")

    for filename in os.listdir(PROMPTS_DIR):
        if filename.endswith('.txt') and filename != 'base_prompt.txt':
            prompt_name = os.path.splitext(filename)[0]
            file_path = os.path.join(PROMPTS_DIR, filename)
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    prompts[prompt_name] = f.read()
            except FileNotFoundError:
                st.warning(f"Prompt file not found: {file_path}")

    return prompts

def get_prompt_names():
    return [name for name in load_prompts().keys() if name != 'base_prompt.txt']

def get_prompt_content(prompt_name):
    prompts = load_prompts()
    return prompts.get(prompt_name, "")

def split_audio(file):
    audio = AudioSegment.from_file(file)
    chunks = []
    for i in range(0, len(audio), AUDIO_SEGMENT_LENGTH):
        chunks.append(audio[i:i+AUDIO_SEGMENT_LENGTH])
    return chunks

def transcribe_audio(audio_file, progress_callback=None):
    try:
        file_extension = os.path.splitext(audio_file)[1].lower()
        if file_extension == '.mp4':
            # Extract audio from mp4
            video = mp.VideoFileClip(audio_file)
            audio = video.audio
            with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as temp_audio:
                audio.write_audiofile(temp_audio.name)
                audio_file = temp_audio.name
            video.close()
        
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