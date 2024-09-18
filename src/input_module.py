import streamlit as st
from src import config
from src.utils import transcribe_audio, process_text_file
from streamlit_mic_recorder import mic_recorder
import tempfile
from pydub import AudioSegment
import time
import os

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
        
        progress_bar.progress(progress)
        percentage = progress * 100
        status_text.text(f"Voortgang: {percentage:.1f}% | Geschatte resterende tijd: {format_time(remaining_time)} (mm:ss)")
    
    start_time = time.time()
    transcript = transcribe_audio(audio_file, progress_callback=update_progress)
    
    progress_bar.progress(1.0)
    status_text.text("Transcriptie voltooid!")
    
    return transcript

def process_multiple_audio_files(uploaded_files):
    st.info(f"{len(uploaded_files)} audiobestanden geüpload. Transcriptie wordt gestart...")
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
                progress_bar.progress(progress)
                status_text.text(f"Voortgang: {progress*100:.1f}% | Bestand {i+1}/{len(uploaded_files)} verwerkt")
            else:
                st.error(f"Transcriptie van bestand {uploaded_file.name} is mislukt.")

        os.unlink(tmp_file_path)

    if full_transcript:
        st.session_state.input_text = full_transcript
        st.success("Alle audiobestanden zijn succesvol verwerkt en getranscribeerd!")
        st.write("Volledige transcript lengte:", len(full_transcript))
        st.write("Eerste 100 karakters van volledig transcript:", full_transcript[:100])
        st.session_state.transcription_complete = True
    else:
        st.error("Transcriptie van alle bestanden is mislukt. Probeer het opnieuw.")

def render_input_step():
    st.session_state.grammar_checked = False  # Reset grammar check flag
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

        if input_method == "Audio uploaden" and not st.session_state.transcription_complete:
            st.markdown("<div class='info-container'>", unsafe_allow_html=True)
            uploaded_file = st.file_uploader("Upload een audio- of videobestand", type=config.ALLOWED_AUDIO_TYPES, key="audio_uploader")
            if uploaded_file:
                st.session_state.uploaded_audio = uploaded_file
                st.button("Verwerk audio", key="process_audio_button", type="primary", on_click=process_uploaded_audio, args=(uploaded_file,))
            st.markdown("</div>", unsafe_allow_html=True)

        elif input_method == "Audio opnemen" and not st.session_state.transcription_complete:
            st.markdown("<div class='info-container'>", unsafe_allow_html=True)
            st.write("Klik op de knop om de opname te starten.")
            st.write("Vergeet niet de volgende onderwerpen te behandelen:")
            st.checkbox("Pensioendatum", key="checklist_pension_date")
            st.checkbox("Arbeidsongeschiktheid", key="checklist_disability")
            st.checkbox("Overlijden", key="checklist_death")
            
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
            if st.button("Verwerk tekst", key="process_text_button"):
                if st.session_state.input_text:
                    st.session_state.transcription_complete = True
                    st.success("Tekst succesvol verwerkt!")
                else:
                    st.warning("Voer eerst tekst in voordat u op 'Verwerk tekst' klikt.")
            st.markdown("</div>", unsafe_allow_html=True)

        elif input_method == "Tekstbestand uploaden" and not st.session_state.transcription_complete:
            st.markdown("<div class='info-container'>", unsafe_allow_html=True)
            uploaded_file = st.file_uploader("Upload een tekstbestand", type=config.ALLOWED_TEXT_TYPES, key="text_file_uploader")
            if uploaded_file:
                st.session_state.uploaded_text = uploaded_file
                st.button("Verwerk bestand", key="process_file_button", on_click=process_uploaded_text, args=(uploaded_file,))
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
        st.button("Volgende", key="next_button", on_click=lambda: setattr(st.session_state, 'step', st.session_state.step + 1))
    else:
        st.button("Volgende", key="next_button", disabled=True)

    # Return the recording state to be used in the main app for navigation control
    return st.session_state.is_recording
    
def process_uploaded_audio(uploaded_file):
    st.info("Audiobestand geüpload. Transcriptie wordt gestart...")
    with st.spinner("Audio wordt verwerkt en getranscribeerd..."):
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp_file:
            tmp_file.write(uploaded_file.getvalue())
            tmp_file_path = tmp_file.name
        st.session_state.input_text = transcribe_with_progress(tmp_file_path)
        if st.session_state.input_text:
            st.success("Audio succesvol verwerkt en getranscribeerd!")
            st.write("Transcript lengte:", len(st.session_state.input_text))
            st.write("Eerste 100 karakters van transcript:", st.session_state.input_text[:100])
            st.session_state.transcription_complete = True
        else:
            st.error("Transcriptie is mislukt. Probeer een ander audiobestand.")

def process_recorded_audio(audio_data):
    with st.spinner("Audio wordt verwerkt en getranscribeerd..."):
        audio_file = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
        audio_file.write(audio_data['bytes'])
        audio_file_path = audio_file.name
        audio_file.close()
        
        st.session_state.input_text = transcribe_with_progress(audio_file_path)
        if st.session_state.input_text:
            st.success("Audio succesvol opgenomen en getranscribeerd!")
            st.write("Transcript lengte:", len(st.session_state.input_text))
            st.write("Eerste 100 karakters van transcript:", st.session_state.input_text[:100])
            st.session_state.transcription_complete = True
        else:
            st.error("Transcriptie is mislukt. Probeer opnieuw op te nemen.")

def process_uploaded_text(uploaded_file):
    st.info("Bestand geüpload. Verwerking wordt gestart...")
    with st.spinner("Bestand wordt verwerkt..."):
        st.session_state.input_text = process_text_file(uploaded_file)
        if st.session_state.input_text:
            st.session_state.transcription_complete = True
            st.success("Bestand succesvol geüpload en verwerkt!")
            st.write("Transcript lengte:", len(st.session_state.input_text))
            st.write("Eerste 100 karakters van transcript:", st.session_state.input_text[:100])
        else:
            st.error("Verwerking is mislukt. Probeer een ander bestand.")