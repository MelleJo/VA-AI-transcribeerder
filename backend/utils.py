import os
from typing import Optional, Tuple
from pydub import AudioSegment
from openai import OpenAI
import tempfile
from moviepy import *
def process_audio_file(file_path: str, chunk_length_ms: int = 60000) -> Tuple[str, bool]:
    """Process audio file and return transcription"""
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    failed_chunks = False
    
    try:
        # Handle MP4 files
        if file_path.endswith('.mp4'):
            video = VideoFileClip(file_path)
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_audio:
                video.audio.write_audiofile(temp_audio.name)
                file_path = temp_audio.name
                video.close()

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
                with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
                    chunk.export(temp_file.name, format='wav')
                    
                    # Transcribe with Whisper
                    with open(temp_file.name, 'rb') as audio_file:
                        transcript = client.audio.transcriptions.create(
                            model="whisper-1",
                            file=audio_file,
                            response_format="text"
                        )
                        transcripts.append(transcript)
                        
                    # Clean up temp file
                    os.unlink(temp_file.name)
                    
            except Exception as e:
                print(f"Error processing chunk {i}: {str(e)}")
                failed_chunks = True
                continue

        return " ".join(transcripts), failed_chunks

    except Exception as e:
        print(f"Error processing audio: {str(e)}")
        return "", True