import os
from src.config import PROMPTS_DIR, AUDIO_MODEL, SUMMARY_MODEL, MAX_TOKENS, TEMPERATURE, AUDIO_SEGMENT_LENGTH, OPENAI_API_KEY
from src.ui_components import estimate_time
import streamlit as st
from PyPDF2 import PdfReader
from docx import Document
from openai import OpenAI
from pydub import AudioSegment
import tempfile
import io
import json
import moviepy.editor as mp
import re
import logging
from groq import Groq

# Add these lines at the beginning of the file
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

client = OpenAI(api_key=OPENAI_API_KEY)
groq_client = Groq(api_key=st.secrets["GROQ_API_KEY"])

# Add this new function
def transcribe_with_groq(audio_file_path):
    try:
        with open(audio_file_path, "rb") as audio_file:
            transcription = groq_client.audio.transcriptions.create(
                file=audio_file,
                model="whisper-large-v3",
                language= "nl",
                response_format="json"
            )
        return transcription.text
    except Exception as e:
        logger.error(f"Error with Groq transcription: {str(e)}")
        return None

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


def split_audio(audio):
    chunks = []
    chunk_length_ms = 60000  # 60 seconds
    for i in range(0, len(audio), chunk_length_ms):
        chunks.append(audio[i:i+chunk_length_ms])
    return chunks

def transcribe_audio(audio_file, progress_callback=None):
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as temp_audio:
            audio = AudioSegment.from_file(audio_file)
            audio.export(temp_audio.name, format="wav")
            
            with open(temp_audio.name, "rb") as audio_file:
                if progress_callback:
                    progress_callback(0, 1, "Groq")
                
                transcript = transcribe_with_groq(audio_file)
                
                if transcript is None and progress_callback:
                    progress_callback(0, 1, "OpenAI")
                    
                    response = client.audio.transcriptions.create(
                        model="whisper-1",
                        file=audio_file,
                        response_format="text"
                    )
                    transcript = response
            
            if progress_callback:
                progress_callback(1, 1, "Groq" if transcript is not None else "OpenAI")
            
            logger.info(f"API used = {'Groq' if transcript is not None else 'OpenAI'}")
            return transcript.strip()
    except Exception as e:
        logger.error(f"An error occurred during audio transcription: {str(e)}")
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
    
def post_process_grammar_check(text):
    client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "Je bent een professionele corrector gespecialiseerd in Nederlandse financiële en verzekeringstermen. Corrigeer eventuele spel- of grammaticafouten in de volgende tekst, met speciale aandacht voor vakspecifieke termen."},
                {"role": "user", "content": text}
            ],
            max_tokens=16384
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        st.error(f"Fout bij grammatica- en spellingscontrole: {str(e)}")
        return text  # Return original text if there's an error

def format_currency(text):
    return re.sub(r'(€)(\d)', r'\1 \2', text)