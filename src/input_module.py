# src/input_module.py

import streamlit as st
from src import config
from src.utils import transcribe_audio, process_text_file
from streamlit_mic_recorder import mic_recorder
import tempfile
from pydub import AudioSegment
import time
import os
from src.ui_components import ui_styled_button, ui_info_box, ui_progress_bar
import logging

logger = logging.getLogger(__name__)

def get_audio_length(file):
    audio = AudioSegment.from_file(file)
    return len(audio) / 1000  # Length in seconds

def format_time(seconds):
    minutes, seconds = divmod(int(seconds), 60)
    return f"{minutes:02d}:{seconds:02d}"

def transcribe_with_progress(audio_file):
    audio_length = get_audio_length(audio_file)
    
    def update_progress(current, total):
        pass  # No operation needed for progress update
    
    transcript = transcribe_audio(audio_file, progress_callback=update_progress)
    
    return transcript

def process_multiple_audio_files(uploaded_files):
    ui_info_box(f"{len(uploaded_files)} audiobestanden geüpload. Transcriptie wordt gestart...", "info")
    full_transcript = ""
    for i, uploaded_file in enumerate(uploaded_files):
        with st.spinner(f"Bestand {i+1}/{len(uploaded_files)} wordt verwerkt en getranscribeerd..."):
            with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp_file:
                tmp_file.write(uploaded_file.getvalue())
                tmp_file_path = tmp_file.name

            transcript = transcribe_with_progress(tmp_file_path)
            if transcript:
                full_transcript += transcript + "\n\n"
            else:
                ui_info_box(f"Transcriptie van bestand {uploaded_file.name} is mislukt.", "error")

        os.unlink(tmp_file_path)

    if full_transcript:
        st.session_state.input_text = full_transcript
        ui_info_box("Alle audiobestanden zijn succesvol verwerkt en getranscribeerd!", "success")
        st.write("Volledige transcript lengte:", len(full_transcript))
        st.write("Eerste 100 karakters van volledig transcript:", full_transcript[:100])
        st.session_state.transcription_complete = True
        return full_transcript
    else:
        ui_info_box("Transcriptie van alle bestanden is mislukt. Probeer het opnieuw.", "error")
        return None

def process_multiple_text_files(uploaded_files):
    ui_info_box(f"{len(uploaded_files)} tekstbestanden geüpload. Verwerking wordt gestart...", "info")
    full_text = ""
    progress_bar = st.progress(0)
    status_text = st.empty()

    for i, uploaded_file in enumerate(uploaded_files):
        with st.spinner(f"Bestand {i+1}/{len(uploaded_files)} wordt verwerkt..."):
            text = process_text_file(uploaded_file)
            if text:
                full_text += text + "\n\n"
                progress = (i + 1) / len(uploaded_files)
                ui_progress_bar(progress, f"{progress*100:.1f}%")
                status_text.text(f"Bestand {i+1}/{len(uploaded_files)} verwerkt")
            else:
                ui_info_box(f"Verwerking van bestand {uploaded_file.name} is mislukt.", "error")

    if full_text:
        st.session_state.input_text = full_text
        ui_info_box("Alle tekstbestanden zijn succesvol verwerkt!", "success")
        st.write("Volledige tekst lengte:", len(full_text))
        st.write("Eerste 100 karakters van volledige tekst:", full_text[:100])
        st.session_state.transcription_complete = True
        return full_text
    else:
        ui_info_box("Verwerking van alle bestanden is mislukt. Probeer het opnieuw.", "error")
        return None

def render_recording_reminders(prompt_type):
    reminders = config.PROMPT_REMINDERS.get(prompt_type, [])
    if reminders:
        st.markdown("### Vergeet niet de volgende onderwerpen te behandelen:")
        
        # Calculate the number of columns based on the number of reminders
        num_columns = min(3, len(reminders))  # Maximum of 3 columns
        cols = st.columns(num_columns)
        
        for i, reminder in enumerate(reminders):
            with cols[i % num_columns]:
                st.markdown(f"""
                <div style="border: 1px solid #ddd; border-radius: 5px; padding: 10px; margin-bottom: 10px; height: 100%;">
                    <h4 style="margin: 0;">{reminder['topic']}</h4>
                    <ul style="margin: 5px 0 0 0; padding-left: 20px;">
                        {"".join(f"<li>{detail}</li>" for detail in reminder['details'])}
                    </ul>
                </div>
                """, unsafe_allow_html=True)

def render_input_step():
    logger.debug("Rendering input step")
    
    input_method = st.radio(
        "Kies invoermethode:",
        ["Audio uploaden", "Audio opnemen", "Tekst schrijven/plakken", "Tekstbestand uploaden"]
    )
    logger.info(f"Selected input method: {input_method}")

    if input_method == "Audio uploaden":
        uploaded_files = st.file_uploader(
            "Upload een of meerdere audio- of videobestanden",
            type=config.ALLOWED_AUDIO_TYPES,
            accept_multiple_files=True
        )
        if uploaded_files:
            logger.info(f"Audio files uploaded: {[file.name for file in uploaded_files]}")
            return process_multiple_audio_files(uploaded_files)

    elif input_method == "Audio opnemen":
        st.write("Klik op de knop om de opname te starten.")
        audio_data = mic_recorder(start_prompt="Start opname", stop_prompt="Stop opname")
        if isinstance(audio_data, dict) and 'bytes' in audio_data:
            logger.info("Audio recording completed")
            return process_recorded_audio(audio_data)

    elif input_method == "Tekst schrijven/plakken":
        text_input = st.text_area(
            "Voer tekst in of plak tekst:",
            height=300,
            key="text_input_area"
        )
        if st.button("Verwerk tekst"):
            logger.info(f"Text input received. Length: {len(text_input)}")
            st.session_state.is_processing = True
            logger.debug(f"is_processing set to True after text input")
            return text_input

    elif input_method == "Tekstbestand uploaden":
        uploaded_files = st.file_uploader(
            "Upload een of meerdere tekstbestanden",
            type=config.ALLOWED_TEXT_TYPES,
            accept_multiple_files=True
        )
        if uploaded_files:
            logger.info(f"Text files uploaded: {[file.name for file in uploaded_files]}")
            return process_multiple_text_files(uploaded_files)

    logger.debug("Input step rendering complete")
    return None

def process_uploaded_audio(uploaded_file):
    logger.info(f"Processing uploaded audio file: {uploaded_file.name}")
    st.info("Audiobestand geüpload. Transcriptie wordt gestart...")
    with st.spinner("Audio wordt verwerkt en getranscribeerd..."):
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp_file:
            tmp_file.write(uploaded_file.getvalue())
            tmp_file_path = tmp_file.name
        
        try:
            logger.debug(f"Transcribing audio file: {tmp_file_path}")
            transcript = transcribe_audio(tmp_file_path)
            if transcript:
                logger.info(f"Transcription successful. Text length: {len(transcript)}")
                st.session_state.is_processing = True
                logger.debug(f"is_processing set to True after transcription")
                return transcript
            else:
                logger.warning("Transcription resulted in empty text")
                st.error("Transcriptie is mislukt. Probeer een ander audiobestand.")
        except Exception as e:
            logger.exception(f"Error during audio transcription: {str(e)}")
            st.error(f"Er is een fout opgetreden tijdens de transcriptie: {str(e)}")
        finally:
            os.unlink(tmp_file_path)
            logger.debug(f"Temporary file removed: {tmp_file_path}")
    return None

def process_recorded_audio(audio_data):
    logger.info("Processing recorded audio")
    with st.spinner("Audio wordt verwerkt en getranscribeerd..."):
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as audio_file:
            audio_file.write(audio_data['bytes'])
            audio_file_path = audio_file.name
        
        try:
            logger.debug(f"Transcribing audio file: {audio_file_path}")
            transcript = transcribe_audio(audio_file_path)
            if transcript:
                logger.info(f"Transcription successful. Text length: {len(transcript)}")
                st.session_state.is_processing = True
                logger.debug(f"is_processing set to True after recorded audio transcription")
                return transcript
            else:
                logger.warning("Transcription resulted in empty text")
                st.error("Transcriptie is mislukt. Probeer opnieuw op te nemen.")
        except Exception as e:
            logger.exception(f"Error during audio transcription: {str(e)}")
            st.error(f"Er is een fout opgetreden tijdens de transcriptie: {str(e)}")
        finally:
            os.unlink(audio_file_path)
            logger.debug(f"Temporary file removed: {audio_file_path}")
    return None

def process_uploaded_text(uploaded_file):
    ui_info_box("Bestand geüpload. Verwerking wordt gestart...", "info")
    with st.spinner("Bestand wordt verwerkt..."):
        text = process_text_file(uploaded_file)
        if text:
            st.session_state.transcription_complete = True
            ui_info_box("Bestand succesvol geüpload en verwerkt!", "success")
            st.write("Tekst lengte:", len(text))
            st.write("Eerste 100 karakters van tekst:", text[:100])
            return text
        else:
            ui_info_box("Verwerking is mislukt. Probeer een ander bestand.", "error")
    return None