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
from streamlit.runtime.uploaded_file_manager import UploadedFile

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
            response = groq_client.audio.transcriptions.create(
                file=audio_file,
                model="whisper-large-v3",
                response_format="text"
            )
            if isinstance(response, str):
                return response
            elif hasattr(response, 'text'):
                return response.text
            else:
                logger.warning(f"Unexpected Groq response format: {type(response)}")
                return None
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

def get_optimal_chunk_length(audio_length_ms: int) -> int:
    """Calculate optimal chunk length to stay under 25MB limit while maximizing size"""
    SAFE_CHUNK_SIZE_MS = 150_000  # 2.5 minutes - reduced for safety
    
    if audio_length_ms <= SAFE_CHUNK_SIZE_MS:
        return audio_length_ms
    
    num_chunks = max(2, audio_length_ms // SAFE_CHUNK_SIZE_MS + 1)
    return audio_length_ms // num_chunks

def split_audio(audio: AudioSegment) -> list:
    """Split audio into optimally sized chunks"""
    total_length = len(audio)
    chunk_length = get_optimal_chunk_length(total_length)
    
    logger.info(f"Splitting {total_length/1000:.2f}s audio into chunks of {chunk_length/1000:.2f}s")
    
    chunks = []
    for i in range(0, total_length, chunk_length):
        chunks.append(audio[i:i + chunk_length])
    return chunks

def transcribe_chunk(chunk_path: str, chunk_num: int, total_chunks: int, progress_callback=None) -> Optional[str]:
    """Transcribe a single chunk with fallback"""
    
    transcript = None
    api_used = None
    
    try:
        transcript = transcribe_with_groq(chunk_path)
        if transcript:
            api_used = "Groq"
    except Exception as e:
        logger.warning(f"Groq transcription attempt failed: {str(e)}")
    
    if transcript is None:
        try:
            transcript = transcribe_with_whisper(chunk_path)
            if transcript:
                api_used = "OpenAI"
        except Exception as e:
            logger.warning(f"Whisper transcription attempt failed: {str(e)}")
    
    if progress_callback and api_used:
        progress = ((chunk_num + 1) / total_chunks) * 100
        progress_callback(current_step=chunk_num, total_steps=total_chunks, step_description=f"Transcriptie met {api_used}")
    
    return transcript

def transcribe_audio(audio_file: Union[str, bytes, 'UploadedFile'], progress_callback=None) -> Optional[str]:
    """Main transcription function with improved memory management"""
    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_file_path = None
            file_extension = None

            if isinstance(audio_file, str):
                temp_file_path = audio_file
                file_extension = os.path.splitext(audio_file)[1].lower()
            elif hasattr(audio_file, 'name'):
                file_extension = os.path.splitext(audio_file.name)[1].lower()
                temp_file_path = os.path.join(temp_dir, f"temp_audio{file_extension}")
                try:
                    # Read file in chunks to avoid memory issues
                    with open(temp_file_path, "wb") as f:
                        CHUNK_SIZE = 8192  # 8KB chunks
                        for chunk in iter(lambda: audio_file.read(CHUNK_SIZE), b''):
                            f.write(chunk)
                except Exception as e:
                    raise Exception(f"Error saving uploaded file: {str(e)}")
            elif isinstance(audio_file, (bytes, bytearray)):
                file_extension = '.wav'
                temp_file_path = os.path.join(temp_dir, f"temp_audio{file_extension}")
                try:
                    with open(temp_file_path, "wb") as f:
                        f.write(audio_file)
                except Exception as e:
                    raise Exception(f"Error saving audio bytes: {str(e)}")
            else:
                raise Exception(f"Unsupported audio file type: {type(audio_file)}")

            if not temp_file_path or not os.path.exists(temp_file_path):
                raise Exception("Failed to create temporary audio file")

            logger.info(f"Processing audio file with extension: {file_extension}")
            
            if file_extension == '.mp4':
                try:
                    video = mp.VideoFileClip(temp_file_path)
                    audio = video.audio
                    mp4_audio_path = os.path.join(temp_dir, "temp_audio.wav")
                    audio.write_audiofile(mp4_audio_path)
                    temp_file_path = mp4_audio_path
                    video.close()
                    logger.info("Successfully converted MP4 to WAV")
                except Exception as e:
                    raise Exception(f"Error converting MP4 to WAV: {str(e)}")

            try:
                logger.info("Loading audio file...")
                audio = AudioSegment.from_file(temp_file_path)
                audio_length = len(audio) / 1000
                
                if audio_length < 0.1:
                    raise Exception("Audio file is too short for transcription. Minimum length is 0.1 seconds.")
                
                chunks = split_audio(audio)
                total_chunks = len(chunks)
                
                # Use Whisper for larger files
                USE_WHISPER_THRESHOLD = 15
                use_whisper = total_chunks > USE_WHISPER_THRESHOLD
                
                logger.info(f"Starting transcription of {total_chunks} chunks using {'Whisper' if use_whisper else 'Groq'}")
                
                transcripts = []
                failed_chunks = []
                
                for i, chunk in enumerate(chunks):
                    chunk_path = os.path.join(temp_dir, f"chunk_{i}.wav")
                    chunk.export(chunk_path, format="wav")
                    
                    logger.info(f"Processing chunk {i+1}/{total_chunks}")
                    
                    try:
                        if use_whisper:
                            transcript = transcribe_with_whisper(chunk_path)
                        else:
                            transcript = transcribe_with_groq(chunk_path)
                            if transcript is None:
                                transcript = transcribe_with_whisper(chunk_path)
                        
                        if transcript:
                            transcripts.append(transcript)
                            logger.info(f"Successfully transcribed chunk {i+1}")
                        else:
                            failed_chunks.append(i)
                            logger.error(f"Failed to transcribe chunk {i+1}")
                    except Exception as e:
                        failed_chunks.append(i)
                        logger.error(f"Failed to transcribe chunk {i+1} due to error: {str(e)}")
                    finally:
                        # Clean up chunk file immediately after processing
                        if os.path.exists(chunk_path):
                            os.unlink(chunk_path)
                    
                    if progress_callback:
                        progress = ((i + 1) / total_chunks) * 100
                        progress_callback(i, total_chunks, f"Transcriptie met {'Whisper' if use_whisper else 'Groq'}")
                
                if failed_chunks:
                    logger.warning(f"Failed chunks: {failed_chunks}")
                    if len(failed_chunks) > total_chunks / 2:
                        raise Exception("Meer dan 50% van de audio kon niet worden getranscribeerd")
                
                full_transcript = " ".join(transcripts)
                
                if not full_transcript.strip():
                    raise Exception("Geen tekst kon worden geëxtraheerd uit de audio")
                
                logger.info(f"Transcription completed successfully with {len(transcripts)} chunks")
                return full_transcript.strip(), bool(failed_chunks)
                
            except Exception as e:
                raise Exception(f"Error processing audio: {str(e)}")
            
    except Exception as e:
        logger.error(f"Transcriptie fout: {str(e)}")
        raise Exception(f"Er is een fout opgetreden tijdens de transcriptie: {str(e)}")
    finally:
        # Force garbage collection
        import gc
        gc.collect()

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
