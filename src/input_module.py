import streamlit as st
from src import config
from src.utils import transcribe_audio, process_text_file
from streamlit_mic_recorder import mic_recorder
import tempfile
from pydub import AudioSegment
import time
import os
from src.ui_components import ui_styled_button, ui_info_box, ui_progress_bar

def get_audio_length(file):
    audio = AudioSegment.from_file(file)
    return len(audio) / 1000  # Length in seconds

def format_time(seconds):
    minutes, seconds = divmod(int(seconds), 60)
    return f"{minutes:02d}:{seconds:02d}"

def transcribe_with_progress(audio_file):
    audio_length = get_audio_length(audio_file)
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    def update_progress(current, total):
        progress = current / total
        elapsed_time = time.time() - start_time
        estimated_total_time = elapsed_time / progress if progress > 0 else audio_length
        remaining_time = max(0, estimated_total_time - elapsed_time)
        
        ui_progress_bar(progress, f"{progress*100:.1f}%")
        status_text.text(f"Geschatte resterende tijd: {format_time(remaining_time)} (mm:ss)")
    
    start_time = time.time()
    transcript = transcribe_audio(audio_file, progress_callback=update_progress)
    
    progress_bar.progress(1.0)
    status_text.text("Transcriptie voltooid!")
    
    return transcript

def process_multiple_audio_files(uploaded_files):
    ui_info_box(f"{len(uploaded_files)} audiobestanden geüpload. Transcriptie wordt gestart...", "info")
    full_transcript = ""
    progress_bar = st.progress(0)
    status_text = st.empty()

    for i, uploaded_file in enumerate(uploaded_files):
        with st.spinner(f"Bestand {i+1}/{len(uploaded_files)} wordt verwerkt en getranscribeerd..."):
            with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp_file:
                tmp_file.write(uploaded_file.getvalue())
                tmp_file_path = tmp_file.name

            transcript = transcribe_with_progress(tmp_file_path)
            if transcript:
                full_transcript += transcript + "\n\n"
                progress = (i + 1) / len(uploaded_files)
                ui_progress_bar(progress, f"{progress*100:.1f}%")
                status_text.text(f"Bestand {i+1}/{len(uploaded_files)} verwerkt")
            else:
                ui_info_box(f"Transcriptie van bestand {uploaded_file.name} is mislukt.", "error")

        os.unlink(tmp_file_path)

    if full_transcript:
        st.session_state.input_text = full_transcript
        ui_info_box("Alle audiobestanden zijn succesvol verwerkt en getranscribeerd!", "success")
        st.write("Volledige transcript lengte:", len(full_transcript))
        st.write("Eerste 100 karakters van volledig transcript:", full_transcript[:100])
        st.session_state.transcription_complete = True
    else:
        ui_info_box("Transcriptie van alle bestanden is mislukt. Probeer het opnieuw.", "error")

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
    st.session_state.grammar_checked = False
    st.markdown("<h2 class='section-title'>Stap 2: Invoer</h2>", unsafe_allow_html=True)
    
    if 'transcription_complete' not in st.session_state:
        st.session_state.transcription_complete = False
    if 'is_recording' not in st.session_state:
        st.session_state.is_recording = False
    if 'input_text' not in st.session_state:
        st.session_state.input_text = ""
    if 'audio_data' not in st.session_state:
        st.session_state.audio_data = None

    if not st.session_state.is_recording:
        st.markdown("<div class='info-container'>", unsafe_allow_html=True)
        input_method = st.radio(
            "Kies invoermethode:",
            ["Audio uploaden", "Meerdere audiobestanden uploaden", "Audio opnemen", "Tekst schrijven/plakken", "Tekstbestand uploaden"],
            key="input_method_radio"
        )
        st.markdown("</div>", unsafe_allow_html=True)

        if input_method == "Audio opnemen" and not st.session_state.transcription_complete:
            st.markdown("<div class='info-container'>", unsafe_allow_html=True)
            st.write("Klik op de knop om de opname te starten.")
            render_recording_reminders(st.session_state.selected_prompt)
            
            audio_data = mic_recorder(key="audio_recorder", start_prompt="Start opname", stop_prompt="Stop opname", use_container_width=True)
            
            if audio_data is not None:
                if isinstance(audio_data, dict) and audio_data.get("state") == "recording":
                    st.session_state.is_recording = True
                    st.rerun()
                elif isinstance(audio_data, dict) and 'bytes' in audio_data:
                    st.session_state.audio_data = audio_data
                    process_recorded_audio(audio_data)
            st.markdown("</div>", unsafe_allow_html=True)

        if input_method == "Audio uploaden" and not st.session_state.transcription_complete:
            st.markdown("<div class='info-container'>", unsafe_allow_html=True)
            uploaded_file = st.file_uploader("Upload een audio- of videobestand", type=config.ALLOWED_AUDIO_TYPES, key="audio_uploader")
            if uploaded_file:
                st.session_state.uploaded_audio = uploaded_file
                ui_styled_button("Verwerk audio", on_click=lambda: process_uploaded_audio(uploaded_file), key="process_audio_button", is_active=True, primary=True)
            st.markdown("</div>", unsafe_allow_html=True)

        elif input_method == "Audio opnemen" and not st.session_state.transcription_complete:
            st.markdown("<div class='info-container'>", unsafe_allow_html=True)
            st.write("Klik op de knop om de opname te starten.")
            render_recording_reminders(st.session_state.selected_prompt)
            
            audio_data = mic_recorder(key="audio_recorder", start_prompt="Start opname", stop_prompt="Stop opname", use_container_width=True)
            
            if audio_data is not None:
                if isinstance(audio_data, dict) and audio_data.get("state") == "recording":
                    st.session_state.is_recording = True
                    st.rerun()
                elif isinstance(audio_data, dict) and 'bytes' in audio_data:
                    st.session_state.audio_data = audio_data
                    process_recorded_audio(audio_data)
            st.markdown("</div>", unsafe_allow_html=True)

        elif input_method == "Tekst schrijven/plakken" and not st.session_state.transcription_complete:
            st.markdown("<div class='info-container'>", unsafe_allow_html=True)
            st.session_state.input_text = st.text_area("Voer tekst in of plak tekst:", height=300, key="text_input_area")
            ui_styled_button("Verwerk tekst", on_click=process_text_input, key="process_text_button", is_active=bool(st.session_state.input_text))
            st.markdown("</div>", unsafe_allow_html=True)

        elif input_method == "Tekstbestand uploaden" and not st.session_state.transcription_complete:
            st.markdown("<div class='info-container'>", unsafe_allow_html=True)
            uploaded_file = st.file_uploader("Upload een tekstbestand", type=config.ALLOWED_TEXT_TYPES, key="text_file_uploader")
            if uploaded_file:
                st.session_state.uploaded_text = uploaded_file
                ui_styled_button("Verwerk bestand", on_click=lambda: process_uploaded_text(uploaded_file), key="process_file_button", is_active=True)
            st.markdown("</div>", unsafe_allow_html=True)

    else:  # This block will only show when recording is in progress
        st.markdown("<div class='info-container'>", unsafe_allow_html=True)
        st.write("Opname is bezig. Klik op 'Stop opname' om de opname te beëindigen.")
        audio_data = mic_recorder(key="audio_recorder_in_progress", start_prompt="Start opname", stop_prompt="Stop opname", use_container_width=True)
        
        if audio_data is not None and isinstance(audio_data, dict) and 'bytes' in audio_data:
            st.session_state.is_recording = False
            st.session_state.audio_data = audio_data
            process_recorded_audio(audio_data)
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

    if st.session_state.transcription_complete:
        st.markdown("<div class='info-container'>", unsafe_allow_html=True)
        st.markdown("<h3 class='section-title'>Transcript</h3>", unsafe_allow_html=True)
        st.session_state.input_text = st.text_area("Bewerk indien nodig:", value=st.session_state.input_text, height=300, key="final_transcript")
        st.markdown("</div>", unsafe_allow_html=True)

    # Add the "Volgende" button with conditional disabling
    if st.session_state.transcription_complete:
        ui_styled_button("Volgende", on_click=lambda: setattr(st.session_state, 'step', st.session_state.step + 1), key="next_button", is_active=True, primary=True)
    else:
        ui_styled_button("Volgende", on_click=None, key="next_button", is_active=False)

    # Return the recording state to be used in the main app for navigation control
    return st.session_state.is_recording
    
def process_uploaded_audio(uploaded_file):
    ui_info_box("Audiobestand geüpload. Transcriptie wordt gestart...", "info")
    with st.spinner("Audio wordt verwerkt en getranscribeerd..."):
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp_file:
            tmp_file.write(uploaded_file.getvalue())
            tmp_file_path = tmp_file.name
        st.session_state.input_text = transcribe_with_progress(tmp_file_path)
        if st.session_state.input_text:
            ui_info_box("Audio succesvol verwerkt en getranscribeerd!", "success")
            st.write("Transcript lengte:", len(st.session_state.input_text))
            st.write("Eerste 100 karakters van transcript:", st.session_state.input_text[:100])
            st.session_state.transcription_complete = True
        else:
            ui_info_box("Transcriptie is mislukt. Probeer een ander audiobestand.", "error")

def process_recorded_audio(audio_data):
    with st.spinner("Audio wordt verwerkt en getranscribeerd..."):
        audio_file = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
        audio_file.write(audio_data['bytes'])
        audio_file_path = audio_file.name
        audio_file.close()
        
        st.session_state.input_text = transcribe_with_progress(audio_file_path)
        if st.session_state.input_text:
            ui_info_box("Audio succesvol opgenomen en getranscribeerd!", "success")
            st.write("Transcript lengte:", len(st.session_state.input_text))
            st.write("Eerste 100 karakters van transcript:", st.session_state.input_text[:100])
            st.session_state.transcription_complete = True
        else:
            ui_info_box("Transcriptie is mislukt. Probeer opnieuw op te nemen.", "error")

def process_uploaded_text(uploaded_file):
    ui_info_box("Bestand geüpload. Verwerking wordt gestart...", "info")
    with st.spinner("Bestand wordt verwerkt..."):
        st.session_state.input_text = process_text_file(uploaded_file)
        if st.session_state.input_text:
            st.session_state.transcription_complete = True
            ui_info_box("Bestand succesvol geüpload en verwerkt!", "success")
            st.write("Transcript lengte:", len(st.session_state.input_text))
            st.write("Eerste 100 karakters van transcript:", st.session_state.input_text[:100])
        else:
            ui_info_box("Verwerking is mislukt. Probeer een ander bestand.", "error")

def process_text_input():
    if st.session_state.input_text:
        st.session_state.transcription_complete = True
        ui_info_box("Tekst succesvol verwerkt!", "success")
    else:
        ui_info_box("Voer eerst tekst in voordat u op 'Verwerk tekst' klikt.", "warning")