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
import re

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

def split_audio(audio):
    chunks = []
    for i in range(0, len(audio), AUDIO_SEGMENT_LENGTH):
        chunks.append(audio[i:i+AUDIO_SEGMENT_LENGTH])
    return chunks

def transcribe_audio(uploaded_file, progress_callback=None):
    try:
        # Create a temporary directory to store the file
        with tempfile.TemporaryDirectory() as temp_dir:
            # Get the file extension
            file_extension = os.path.splitext(uploaded_file.name)[1].lower()
            
            # Save the uploaded file to the temporary directory
            temp_file_path = os.path.join(temp_dir, f"temp_audio{file_extension}")
            with open(temp_file_path, "wb") as f:
                f.write(uploaded_file.getvalue())
            
            # Handle mp4 files (convert to audio)
            if file_extension == '.mp4':
                video = mp.VideoFileClip(temp_file_path)
                audio = video.audio
                temp_audio_path = os.path.join(temp_dir, "temp_audio.wav")
                audio.write_audiofile(temp_audio_path)
                temp_file_path = temp_audio_path
                video.close()
            
            # Load the audio file
            audio = AudioSegment.from_file(temp_file_path)
            
            # Split the audio into chunks
            chunks = split_audio(audio)
            total_chunks = len(chunks)
            full_transcript = ""

            for i, chunk in enumerate(chunks):
                chunk_path = os.path.join(temp_dir, f"chunk_{i}.wav")
                chunk.export(chunk_path, format="wav")
                
                with open(chunk_path, "rb") as audio_chunk:
                    response = client.audio.transcriptions.create(
                        model=AUDIO_MODEL,
                        file=audio_chunk,
                        response_format="text"
                    )
                    full_transcript += response + " "

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