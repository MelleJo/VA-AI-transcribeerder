# utils.py

import os
from src.config import PROMPTS_DIR, AUDIO_MODEL, SUMMARY_MODEL, MAX_TOKENS, TEMPERATURE, AUDIO_SEGMENT_LENGTH, get_openai_api_key
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
from concurrent.futures import ThreadPoolExecutor, TimeoutError
from typing import Optional, Union

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize clients
client = OpenAI(api_key=get_openai_api_key())
groq_client = Groq(api_key=st.secrets["GROQ_API_KEY"])

def transcribe_with_groq(audio_file_path: str, timeout: int = 10) -> Optional[str]:
    """Attempt to transcribe with Groq with a timeout"""
    try:
        with open(audio_file_path, "rb") as audio_file:
            transcription = groq_client.audio.transcriptions.create(
                file=audio_file,
                model="whisper-large-v3",
                response_format="text"
            )
            return transcription.text if transcription else None
    except Exception as e:
        logger.warning(f"Groq transcription failed: {str(e)}")
        return None

def transcribe_with_whisper(audio_file_path: str) -> Optional[str]:
    """Attempt to transcribe with OpenAI Whisper"""
    try:
        with open(audio_file_path, "rb") as audio_file:
            response = client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
                response_format="text"
            )
            return response
    except Exception as e:
        logger.warning(f"Whisper transcription failed: {str(e)}")
        return None

def split_audio(audio: AudioSegment, chunk_length_ms: int = 60000) -> list:
    """Split audio into manageable chunks"""
    chunks = []
    for i in range(0, len(audio), chunk_length_ms):
        chunks.append(audio[i:i + chunk_length_ms])
    return chunks

def transcribe_chunk(chunk_path: str, chunk_num: int, total_chunks: int, progress_callback=None) -> Optional[str]:
    """Transcribe a single chunk with fallback"""
    
    # Try Groq first
    transcript = transcribe_with_groq(chunk_path)
    api_used = "Groq"
    
    # If Groq fails, immediately try Whisper
    if transcript is None:
        transcript = transcribe_with_whisper(chunk_path)
        api_used = "OpenAI"
    
    if progress_callback:
        progress = (chunk_num + 1) / total_chunks * 100
        progress_callback(chunk_num, total_chunks, f"Transcriptie met {api_used}")
    
    return transcript

def transcribe_audio(audio_file: Union[str, bytes], progress_callback=None) -> Optional[str]:
    """Main transcription function with improved error handling and no delays"""
    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            # Handle input file
            if isinstance(audio_file, str):
                temp_file_path = audio_file
                file_extension = os.path.splitext(audio_file)[1].lower()
            else:
                file_extension = os.path.splitext(audio_file.name)[1].lower()
                temp_file_path = os.path.join(temp_dir, f"temp_audio{file_extension}")
                with open(temp_file_path, "wb") as f:
                    f.write(audio_file.getvalue())
            
            # Convert MP4 if needed
            if file_extension == '.mp4':
                video = mp.VideoFileClip(temp_file_path)
                audio = video.audio
                temp_audio_path = os.path.join(temp_dir, "temp_audio.wav")
                audio.write_audiofile(temp_audio_path)
                temp_file_path = temp_audio_path
                video.close()
            
            # Process audio
            audio = AudioSegment.from_file(temp_file_path)
            chunks = split_audio(audio)
            total_chunks = len(chunks)
            transcripts = []
            failed_chunks = []

            # Process each chunk
            for i, chunk in enumerate(chunks):
                chunk_path = os.path.join(temp_dir, f"chunk_{i}.wav")
                chunk.export(chunk_path, format="wav")
                
                transcript = transcribe_chunk(chunk_path, i, total_chunks, progress_callback)
                
                if transcript:
                    transcripts.append(transcript)
                else:
                    failed_chunks.append(i)
                    logger.error(f"Failed to transcribe chunk {i}")
            
            # Handle failed chunks
            if failed_chunks:
                logger.warning(f"Failed chunks: {failed_chunks}")
                if len(failed_chunks) > total_chunks / 2:
                    raise Exception("Meer dan 50% van de audio kon niet worden getranscribeerd")
            
            # Combine successful transcripts
            full_transcript = " ".join(transcripts)
            
            if not full_transcript.strip():
                raise Exception("Geen tekst kon worden geëxtraheerd uit de audio")
            
            return full_transcript.strip()
            
    except Exception as e:
        logger.error(f"Transcriptie fout: {str(e)}")
        raise Exception(f"Er is een fout opgetreden tijdens de transcriptie: {str(e)}")

def load_prompts():
    """Load prompt files"""
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
    """Get list of available prompts"""
    return [name for name in load_prompts().keys() if name != 'base_prompt.txt']

def get_prompt_content(prompt_name):
    """Get content of specific prompt"""
    prompts = load_prompts()
    return prompts.get(prompt_name, "")

def process_text_file(file):
    """Process uploaded text files"""
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
        st.error(f"Error processing file: {str(e)}")
        return None

def process_audio_input(audio_data):
    """Process audio input data"""
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as temp_audio:
            temp_audio.write(audio_data['bytes'])
            audio_file_path = temp_audio.name
        return audio_file_path
    except Exception as e:
        st.error(f"Error processing audio input: {str(e)}")
        return None

def post_process_grammar_check(text):
    """Perform grammar check using GPT"""
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
        logger.error(f"Grammar check failed: {str(e)}")
        return text

def format_currency(text):
    """Format currency values consistently"""
    return re.sub(r'(€)(\d)', r'\1 \2', text)