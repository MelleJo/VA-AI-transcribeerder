import streamlit as st
from src import config
from src.utils import transcribe_audio, process_text_file, get_prompt_content
from src.summary_and_output_module import generate_summary
from streamlit_mic_recorder import mic_recorder
import tempfile
from pydub import AudioSegment
import time
import os
from src.ui_components import ui_styled_button, ui_info_box, ui_progress_bar, full_screen_loader, add_loader_css, estimate_time
from src.progress_utils import update_progress
import logging

# Set up logger
logging.basicConfig(level=logging.ERROR)
logger = logging.getLogger(__name__)

def get_audio_length(file):
    audio = AudioSegment.from_file(file)
    return len(audio) / 1000  # Length in seconds

def format_time(seconds):
    minutes, seconds = divmod(int(seconds), 60)
    return f"{minutes:02d}:{seconds:02d}"

def transcribe_with_progress(audio_file_path):
    try:
        total_steps = 100  # Example total steps, adjust as needed
        start_time = time.time()
        progress_placeholder = st.empty()
        
        def progress_callback(current_step, total_steps, step_description):
            update_progress(progress_placeholder, step_description, current_step, total_steps)
        
        text = transcribe_audio(audio_file_path, progress_callback=progress_callback)
        
        if text:
            # Signal completion explicitly
            progress_placeholder.markdown("""
                <div class="progress-container">
                    <div class="progress-bar" style="width: 100%;"></div>
                </div>
                <p>Transcriptie voltooid ✓</p>
                """, unsafe_allow_html=True)
            return text
        else:
            raise Exception("Transcriptie leverde geen tekst op")
            
    except Exception as e:
        logger.error(f"Transcriptie fout: {str(e)}")
        st.error("Er is een fout opgetreden tijdens de transcriptie. Probeer het opnieuw.")
        return None
    finally:
        # Force UI update
        st.session_state.update({
            'processing_complete': True,
            'current_step': 'input_selection'
        })

def process_multiple_audio_files(uploaded_files):
    ui_info_box(f"{len(uploaded_files)} audiobestanden geüpload. Transcriptie wordt gestart...", "info")
    full_transcript = ""
    progress_bar = st.progress(0)
    status_text = st.empty()

    try:
        for i, uploaded_file in enumerate(uploaded_files):
            with st.spinner(f"Bestand {i+1}/{len(uploaded_files)} wordt verwerkt en getranscribeerd..."):
                transcript = transcribe_with_progress(uploaded_file)
                if transcript:
                    full_transcript += str(transcript) + "\n\n"
                    progress = (i + 1) / len(uploaded_files)
                    ui_progress_bar(progress, f"{progress*100:.1f}%")
                    status_text.text(f"Bestand {i+1}/{len(uploaded_files)} verwerkt")
                else:
                    ui_info_box(f"Transcriptie van bestand {uploaded_file.name} is mislukt.", "error")
                    logger.error(f"Transcriptie van bestand {uploaded_file.name} is mislukt.")

        if full_transcript:
            st.session_state.input_text = full_transcript
            st.session_state.transcription_complete = True
            ui_info_box("Alle audiobestanden zijn succesvol verwerkt en getranscribeerd!", "success")
            return True
        else:
            ui_info_box("Transcriptie van alle bestanden is mislukt. Probeer het opnieuw.", "error")
            return False
    except Exception as e:
        logger.error("Error processing multiple audio files: %s", e)
        ui_info_box(f"Er is een fout opgetreden: {str(e)}", "error")
        return False

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
    else:
        ui_info_box("Verwerking van alle bestanden is mislukt. Probeer het opnieuw.", "error")

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
    st.info("Tip: Spreek je voornaam ook in aan het begin van de opname, dan voegt de AI dit toe aan de samenvatting.")

def render_input_step(on_input_complete):
    st.session_state.grammar_checked = False
    st.markdown("<h2 class='section-title'></h2>", unsafe_allow_html=True)
    
    # Initialize session state variables if not present
    if 'is_processing' not in st.session_state:
        st.session_state.is_processing = False
    
    if not st.session_state.is_processing:
        # Define input_method selection
        input_method = st.radio(
            "Selecteer een invoermethode:",
            ("Meerdere audiobestanden uploaden", "Enkele audio- of videobestand uploaden", "Tekstbestand uploaden", "Tekst invoeren")
        )
        
        if input_method == "Meerdere audiobestanden uploaden":
            st.markdown("<div class='info-container'>", unsafe_allow_html=True)
            uploaded_files = st.file_uploader(
                "Upload meerdere audio- of videobestanden",
                type=config.ALLOWED_AUDIO_TYPES,
                key="multi_audio_uploader",
                accept_multiple_files=True
            )
            if uploaded_files:
                st.session_state.is_processing = True
                if process_multiple_audio_files(uploaded_files):
                    on_input_complete()
                st.session_state.is_processing = False
            st.markdown("</div>", unsafe_allow_html=True)
            
        # [Rest of the input methods...]

    # Show transcript editor if transcription is complete
    if st.session_state.transcription_complete:
        st.markdown("<div class='info-container'>", unsafe_allow_html=True)
        st.markdown("<h3 class='section-title'>Transcript</h3>", unsafe_allow_html=True)
        st.session_state.input_text = st.text_area(
            "Bewerk indien nodig:",
            value=st.session_state.input_text,
            height=300,
            key=f"final_transcript_{hash(st.session_state.input_text)}"
        )
        st.markdown("</div>", unsafe_allow_html=True)

    # Return recording state
    return st.session_state.get('is_recording', False)

def process_uploaded_audio(uploaded_file, on_input_complete):
    st.session_state.transcription_complete = False
    with st.spinner("Audio wordt verwerkt en getranscribeerd..."):
        try:
            if not uploaded_file:
                raise Exception("Geen audiobestand geüpload")

            logger.info(f"Processing uploaded file: {uploaded_file.name}")
            
            # First try to transcribe
            st.session_state.input_text = transcribe_with_progress(uploaded_file)
            
            if st.session_state.input_text:
                st.success("Audio succesvol verwerkt en getranscribeerd!")
                st.write("Transcript lengte:", len(st.session_state.input_text))
                st.write("Eerste 100 karakters van transcript:", st.session_state.input_text[:100])
                st.session_state.transcription_complete = True
                
                # Now try to generate summary
                try:
                    if 'base_prompt' in st.session_state and 'selected_prompt' in st.session_state:
                        logger.info("Generating summary...")
                        summary = generate_summary(
                            st.session_state.input_text,
                            st.session_state.base_prompt,
                            get_prompt_content(st.session_state.selected_prompt)
                        )
                        if summary:
                            st.session_state.summary = summary
                            st.session_state.summaries = [{"type": "summary", "content": summary}]
                            st.session_state.current_version = 0
                            logger.info("Summary generated successfully")
                        else:
                            logger.error("Summary generation returned None")
                            st.error("Er is een fout opgetreden bij het genereren van de samenvatting.")
                    else:
                        logger.error("Missing required prompts for summary generation")
                        st.error("Ontbrekende prompts voor het genereren van de samenvatting.")
                except Exception as e:
                    logger.error(f"Error generating summary: {str(e)}")
                    st.error(f"Fout bij het genereren van de samenvatting: {str(e)}")
                
                on_input_complete()
            else:
                st.error("Transcriptie is mislukt. Probeer een ander audiobestand.")
        except Exception as e:
            logger.error(f"Error processing audio: {str(e)}")
            st.error(f"Er is een fout opgetreden: {str(e)}")

def process_recorded_audio(audio_data, on_input_complete):
    with st.spinner("Audio wordt verwerkt en getranscribeerd..."):
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as audio_file:
                audio_file.write(audio_data['bytes'])
                tmp_file_path = audio_file.name
                
            try:
                st.session_state.input_text = transcribe_with_progress(tmp_file_path)
                
                if st.session_state.input_text:
                    ui_info_box("Audio succesvol opgenomen en getranscribeerd!", "success")
                    st.write("Transcript lengte:", len(st.session_state.input_text))
                    st.write("Eerste 100 karakters van transcript:", st.session_state.input_text[:100])
                    st.session_state.transcription_complete = True
                    # Force state update and move to next step
                    on_input_complete()
                    st.rerun()  # Force refresh
                else:
                    ui_info_box("Transcriptie is mislukt. Probeer opnieuw op te nemen.", "error")
            finally:
                # Always clean up temp file
                if os.path.exists(tmp_file_path):
                    os.unlink(tmp_file_path)
                
        except Exception as e:
            ui_info_box(f"Er is een fout opgetreden: {str(e)}", "error")
            if os.path.exists(tmp_file_path):
                os.unlink(tmp_file_path)

def process_uploaded_text(uploaded_file, on_input_complete):
    ui_info_box("Bestand geüpload. Verwerking wordt gestart...", "info")
    with st.spinner("Bestand wordt verwerkt..."):
        st.session_state.input_text = process_text_file(uploaded_file)
        if st.session_state.input_text:
            st.session_state.transcription_complete = True
            ui_info_box("Bestand succesvol geüpload en verwerkt!", "success")
            st.write("Tekst lengte:", len(st.session_state.input_text))
            st.write("Eerste 100 karakters van tekst:", st.session_state.input_text[:100])
            on_input_complete()
        else:
            ui_info_box("Verwerking is mislukt. Probeer een ander bestand.", "error")

def process_text_input(on_input_complete):
    if st.session_state.input_text:
        st.session_state.transcription_complete = True
        ui_info_box("Tekst succesvol verwerkt!", "success")
        on_input_complete()
    else:
        ui_info_box("Voer eerst tekst in voordat u op 'Verwerk tekst' klikt.", "warning")

def render_upload_input(on_input_complete):
    uploaded_file = st.file_uploader("Upload een audio- of tekstbestand", type=config.ALLOWED_AUDIO_TYPES + config.ALLOWED_TEXT_TYPES)
    if uploaded_file:
        try:
            if uploaded_file.type.startswith('audio/') or uploaded_file.name.endswith('.mp4'):
                with st.spinner("Audio wordt verwerkt en getranscribeerd..."):
                    st.session_state.input_text = transcribe_audio(uploaded_file)
            else:
                st.session_state.input_text = process_text_file(uploaded_file)
            st.text_area("Transcript:", value=st.session_state.input_text, height=300)
            on_input_complete()
        except Exception as e:
            st.error(f"Er is een fout opgetreden bij het verwerken van het bestand: {str(e)}")

def render_audio_input(on_stop_recording):
    audio_data = mic_recorder(start_prompt="Start opname", stop_prompt="Stop opname")
    if audio_data and isinstance(audio_data, dict) and 'bytes' in audio_data:
        st.session_state.input_text = transcribe_audio(audio_data)
        st.text_area("Transcript:", value=st.session_state.input_text, height=300)
        on_stop_recording()

def render_text_input(on_input_complete):
    st.session_state.input_text = st.text_area("Voer tekst in:", height=300)
