import streamlit as st
from src import config
from src.utils import transcribe_audio, process_text_file
from streamlit_mic_recorder import mic_recorder
import tempfile
from pydub import AudioSegment
import time
import os

def get_audio_length(file):
    """
    Get the length of an audio file in seconds.
    
    Args:
        file: File-like object containing audio data.
    
    Returns:
        float: Length of the audio in seconds.
    """
    audio = AudioSegment.from_file(file)
    return len(audio) / 1000

def format_time(seconds):
    """
    Format time in seconds to a string representation.
    
    Args:
        seconds (float): Time in seconds.
    
    Returns:
        str: Formatted time string (MM:SS).
    """
    minutes, seconds = divmod(int(seconds), 60)
    return f"{minutes:02d}:{seconds:02d}"

def transcribe_with_progress(audio_file):
    """
    Transcribe an audio file with a progress indicator.
    
    Args:
        audio_file: Path to the audio file.
    
    Returns:
        str: Transcribed text.
    """
    audio_length = get_audio_length(audio_file)
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    def update_progress(current, total):
        progress = current / total
        elapsed_time = time.time() - start_time
        estimated_total_time = elapsed_time / progress if progress > 0 else audio_length
        remaining_time = max(0, estimated_total_time - elapsed_time)
        
        progress_bar.progress(progress)
        status_text.text(f"Geschatte resterende tijd: {format_time(remaining_time)}")
    
    start_time = time.time()
    transcript = transcribe_audio(audio_file, progress_callback=update_progress)
    
    progress_bar.progress(1.0)
    status_text.text("Transcriptie voltooid!")
    
    return transcript

def handle_audio_recording():
    """
    Handle audio recording using the microphone.
    
    Returns:
        str: Transcribed text from the recorded audio.
    """
    st.write("Klik op de knop om de opname te starten.")
    
    audio_data = mic_recorder(
        key="audio_recorder",
        start_prompt="Start opname",
        stop_prompt="Stop opname",
        use_container_width=True
    )
    
    if audio_data is not None and isinstance(audio_data, dict) and 'bytes' in audio_data:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as temp_audio:
            temp_audio.write(audio_data['bytes'])
            audio_file_path = temp_audio.name
        
        transcript = transcribe_with_progress(audio_file_path)
        os.unlink(audio_file_path)
        
        return transcript
    
    return None

def handle_file_upload():
    """
    Handle file upload for audio or text files.
    
    Returns:
        str: Transcribed text from audio or content of text file.
    """
    uploaded_file = st.file_uploader(
        "Upload een audio- of tekstbestand",
        type=config.ALLOWED_AUDIO_TYPES + config.ALLOWED_TEXT_TYPES
    )
    
    if uploaded_file:
        if uploaded_file.type in config.ALLOWED_AUDIO_TYPES:
            with tempfile.NamedTemporaryFile(delete=False, suffix="." + uploaded_file.type.split("/")[-1]) as temp_file:
                temp_file.write(uploaded_file.getvalue())
                return transcribe_with_progress(temp_file.name)
        else:
            return process_text_file(uploaded_file)
    
    return None

def handle_text_input():
    """
    Handle direct text input from the user.
    
    Returns:
        str: User-input text.
    """
    return st.text_area("Voer tekst in of plak tekst:", height=300)

def render_input_step():
    """
    Render the input step interface.
    
    Returns:
        tuple: (input_method, input_text)
    """
    st.subheader("Stap 2: Invoer")
    
    input_method = st.radio(
        "Kies invoermethode:",
        ["Audio opnemen", "Bestand uploaden", "Tekst schrijven/plakken"]
    )
    
    if input_method == "Audio opnemen":
        input_text = handle_audio_recording()
    elif input_method == "Bestand uploaden":
        input_text = handle_file_upload()
    else:
        input_text = handle_text_input()
    
    return input_method, input_text