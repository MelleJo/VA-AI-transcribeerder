import os
from src.config import PROMPTS_DIR, AUDIO_MODEL, SUMMARY_MODEL, MAX_TOKENS, TEMPERATURE, AUDIO_SEGMENT_LENGTH, OPENAI_API_KEY
import streamlit as st
from PyPDF2 import PdfReader
from docx import Document
from openai import OpenAI
from pydub import AudioSegment
import tempfile
import io
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

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

def split_audio(file_path, max_duration_ms=AUDIO_SEGMENT_LENGTH):
    audio = AudioSegment.from_file(file_path)
    chunks = []
    for i in range(0, len(audio), max_duration_ms):
        chunks.append(audio[i:i+max_duration_ms])
    return chunks

def transcribe_audio(file_path):
    if st.session_state.get('transcription_complete', False):
        return st.session_state.get('transcript', '')

    logger.debug(f"Starting transcribe_audio for file: {file_path}")
    transcript_text = ""
    with st.spinner('Audio segmentatie wordt gestart...'):
        try:
            audio_segments = split_audio(file_path)
            logger.debug(f"Audio split into {len(audio_segments)} segments")
        except Exception as e:
            logger.error(f"Error splitting audio: {str(e)}")
            st.error(f"Fout bij het segmenteren van het audio: {str(e)}")
            return "Segmentatie mislukt."

    total_segments = len(audio_segments)
    progress_bar = st.progress(0)
    progress_text = st.empty()
    progress_text.text("Start transcriptie...")
    for i, segment in enumerate(audio_segments):
        logger.debug(f"Processing segment {i+1} of {total_segments}")
        progress_text.text(f'Bezig met verwerken van segment {i+1} van {total_segments} - {((i+1)/total_segments*100):.2f}% voltooid')
        with tempfile.NamedTemporaryFile(delete=True, suffix='.wav') as temp_file:
            segment.export(temp_file.name, format="wav")
            logger.debug(f"Segment exported to temporary file: {temp_file.name}")
            with open(temp_file.name, "rb") as audio_file:
                try:
                    transcription_response = client.audio.transcriptions.create(
                        file=audio_file,
                        model=AUDIO_MODEL,
                        response_format="text"
                    )
                    logger.debug(f"Transcription response received for segment {i+1}")

                    if isinstance(transcription_response, str):
                        response_content = transcription_response
                    else:
                        response_content = ""

                    logger.debug(f"Transcription response content: {response_content}")
                    transcript_text += response_content + " "
                except Exception as e:
                    logger.error(f"Error transcribing segment {i+1}: {str(e)}")
                    st.error(f"Fout bij het transcriberen van segment {i+1}: {str(e)}")
        progress_bar.progress((i + 1) / total_segments)
    progress_text.success("Transcriptie voltooid.")
    logger.debug(f"Transcription completed. Total length: {len(transcript_text)}")
    st.info(f"Transcript gegenereerd. Lengte: {len(transcript_text)}")
    
    st.session_state['transcription_complete'] = True
    st.session_state['transcript'] = transcript_text.strip()
    
    return transcript_text.strip()

def process_audio_input(audio_data):
    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp_audio:
        tmp_audio.write(audio_data['bytes'])
        tmp_audio.flush()
        tmp_audio_path = tmp_audio.name
    return tmp_audio_path

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

print("utils.py loaded successfully")