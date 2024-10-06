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
    else:
        ui_info_box("Transcriptie van alle bestanden is mislukt. Probeer het opnieuw.", "error")

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

def render_input_step(on_input_complete):
    st.markdown("<h2 class='section-title'>Stap 2: Invoer</h2>", unsafe_allow_html=True)
    
    input_method = st.radio(
        "Kies invoermethode:",
        ["Audio uploaden", "Audio opnemen", "Tekst schrijven/plakken", "Tekstbestand uploaden"]
    )

    if input_method == "Audio uploaden":
        uploaded_file = st.file_uploader(
            "Upload een audio- of videobestand",
            type=config.ALLOWED_AUDIO_TYPES
        )
        if uploaded_file:
            process_uploaded_audio(uploaded_file, on_input_complete)

    elif input_method == "Audio opnemen":
        st.write("Klik op de knop om de opname te starten.")
        audio_data = mic_recorder(start_prompt="Start opname", stop_prompt="Stop opname")
        if isinstance(audio_data, dict) and 'bytes' in audio_data:
            process_recorded_audio(audio_data, on_input_complete)

    elif input_method == "Tekst schrijven/plakken":
        st.session_state.input_text = st.text_area(
            "Voer tekst in of plak tekst:",
            height=300,
            key="text_input_area"
        )
        if st.button("Verwerk tekst"):
            process_text_input(on_input_complete)

    elif input_method == "Tekstbestand uploaden":
        uploaded_file = st.file_uploader(
            "Upload een tekstbestand",
            type=config.ALLOWED_TEXT_TYPES
        )
        if uploaded_file:
            st.session_state.input_text = process_text_file(uploaded_file)
            if st.session_state.input_text:
                on_input_complete()

    return False  # is_recording flag (always False in this simplified version)

def process_uploaded_audio(uploaded_file, on_input_complete):
    ui_info_box("Audiobestand geüpload. Transcriptie wordt gestart...", "info")
    with st.spinner("Audio wordt verwerkt en getranscribeerd..."):
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp_file:
            tmp_file.write(uploaded_file.getvalue())
            tmp_file_path = tmp_file.name
        
        st.session_state.input_text = transcribe_audio(tmp_file_path)
        if st.session_state.input_text:
            on_input_complete()
        else:
            ui_info_box("Transcriptie is mislukt. Probeer een ander audiobestand.", "error")
        os.unlink(tmp_file_path)  # Clean up the temporary file

def process_recorded_audio(audio_data, on_input_complete):
    with st.spinner("Audio wordt verwerkt en getranscribeerd..."):
        audio_file = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
        audio_file.write(audio_data['bytes'])
        audio_file_path = audio_file.name
        audio_file.close()
        
        st.session_state.input_text = transcribe_audio(audio_file_path)
        if st.session_state.input_text:
            on_input_complete()
        else:
            ui_info_box("Transcriptie is mislukt. Probeer opnieuw op te nemen.", "error")
        os.unlink(audio_file_path)  # Clean up the temporary file

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
    st.session_state.input_text = st.text_area("Voer tekst in:", height=300, on_change=on_input_complete)
