import os
from typing import Optional, Tuple
from pydub import AudioSegment
from openai import OpenAI
import tempfile
from moviepy import *
import shutil

def cleanup_temp_file(file_path: str):
    """Clean up temporary file"""
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
    except Exception as e:
        print(f"Error cleaning up temp file: {str(e)}")

def process_audio_file(file_path: str, chunk_length_ms: int = 60000) -> Tuple[str, bool]:
    """Process audio file and return transcription"""
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    failed_chunks = False
    temp_files = []
    
    try:
        # Handle MP4 files
        if file_path.endswith('.mp4'):
            video = VideoFileClip(file_path)
            temp_audio = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)
            temp_files.append(temp_audio.name)
            video.audio.write_audiofile(temp_audio.name)
            file_path = temp_audio.name
            video.close()

        # Load audio file
        audio = AudioSegment.from_file(file_path)
        
        # Split audio into chunks if it's too long
        if len(audio) > chunk_length_ms:
            chunks = [audio[i:i + chunk_length_ms] 
                     for i in range(0, len(audio), chunk_length_ms)]
        else:
            chunks = [audio]

        transcripts = []
        
        for i, chunk in enumerate(chunks):
            try:
                # Export chunk to temporary file
                temp_chunk = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)
                temp_files.append(temp_chunk.name)
                chunk.export(temp_chunk.name, format='wav')
                
                # Transcribe with Whisper
                with open(temp_chunk.name, 'rb') as audio_file:
                    transcript = client.audio.transcriptions.create(
                        model="whisper-1",
                        file=audio_file,
                        response_format="text"
                    )
                    transcripts.append(transcript)
                    
            except Exception as e:
                print(f"Error processing chunk {i}: {str(e)}")
                failed_chunks = True
                continue
            
            finally:
                cleanup_temp_file(temp_chunk.name)

        return " ".join(transcripts), failed_chunks

    except Exception as e:
        print(f"Error processing audio: {str(e)}")
        return "", True
        
    finally:
        # Clean up all temporary files
        for temp_file in temp_files:
            cleanup_temp_file(temp_file)

def ensure_temp_dir():
    """Ensure temporary directory exists"""
    temp_dir = "temp"
    if not os.path.exists(temp_dir):
        os.makedirs(temp_dir)
    return temp_dir