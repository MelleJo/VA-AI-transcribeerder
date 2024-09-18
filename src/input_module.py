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
                full_transcript += f"--- Transcript van bestand {i+1}: {uploaded_file.name} ---\n\n{transcript}\n\n"
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
    
    if 'transcription_complete' not in st.session_state:
        st.session_state.transcription_complete = False
    if 'is_recording' not in st.session_state:
        st.session_state.is_recording = False
    if 'input_text' not in st.session_state:
        st.session_state.input_text = ""
    if 'audio_data' not in st.session_state:
        st.session_state.audio_data = None

    st.markdown("<div class='info-container'>", unsafe_allow_html=True)
    st.markdown("<h3 class='section-subtitle'>Gespreksinvoer</h3>", unsafe_allow_html=True)
    st.markdown("<p class='info-text'>In deze stap voert u uw gesprek in. U kunt kiezen uit verschillende methoden om uw gesprek toe te voegen. Na het invoeren wordt de tekst verwerkt en kunt u deze indien nodig bewerken voordat u verdergaat.</p>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("<div class='info-container'>", unsafe_allow_html=True)
    st.markdown("<h4 class='section-subtitle'>Selecteer invoermethode</h4>", unsafe_allow_html=True)
    st.markdown("<p class='info-text'>Kies de methode die het beste bij uw situatie past om uw gesprek in te voeren.</p>", unsafe_allow_html=True)

    if not st.session_state.is_recording:
        input_method = st.radio(
            "Hoe wilt u uw gesprek invoeren?",
            ["🎤 Audio uploaden", "📁 Meerdere audiobestanden uploaden", "🎙️ Audio opnemen", "✏️ Tekst schrijven/plakken", "📄 Tekstbestand uploaden"],
            key="input_method_radio"
        )
        st.markdown("</div>", unsafe_allow_html=True)

        if input_method == "🎤 Audio uploaden" and not st.session_state.transcription_complete:
            render_audio_upload()
        elif input_method == "📁 Meerdere audiobestanden uploaden" and not st.session_state.transcription_complete:
            render_multiple_audio_upload()
        elif input_method == "🎙️ Audio opnemen" and not st.session_state.transcription_complete:
            render_audio_recording()
        elif input_method == "✏️ Tekst schrijven/plakken" and not st.session_state.transcription_complete:
            render_text_input()
        elif input_method == "📄 Tekstbestand uploaden" and not st.session_state.transcription_complete:
            render_text_file_upload()
    else:  # This block will only show when recording is in progress
        render_recording_in_progress()

    if st.session_state.transcription_complete:
        render_transcript_editor()

    # Add the "Volgende" button with conditional disabling
    st.markdown("<div class='nav-buttons'>", unsafe_allow_html=True)
    if st.session_state.transcription_complete:
        st.button("Volgende", key="next_button", on_click=lambda: setattr(st.session_state, 'step', st.session_state.step + 1))
    else:
        st.markdown("""
        <div class="tooltip">
            <button class="stButton" disabled>Volgende</button>
            <span class="tooltiptext">Verwerk eerst de invoer om door te gaan</span>
        </div>
        """, unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

    # Return the recording state to be used in the main app for navigation control
    return st.session_state.is_recording

def render_audio_upload():
    st.markdown("<div class='info-container'>", unsafe_allow_html=True)
    st.markdown("<h4 class='section-subtitle'>Upload een audiobestand</h4>", unsafe_allow_html=True)
    st.markdown("<p class='info-text'>Upload een audio- of videobestand om te transcriberen. Ondersteunde formaten: MP3, WAV, M4A, MP4.</p>", unsafe_allow_html=True)
    uploaded_file = st.file_uploader("Kies een bestand", type=config.ALLOWED_AUDIO_TYPES, key="audio_uploader")
    if uploaded_file:
        st.session_state.uploaded_audio = uploaded_file
        file_details = {"Bestandsnaam": uploaded_file.name, "Bestandsgrootte": f"{uploaded_file.size / 1024:.2f} KB"}
        st.json(file_details)
        if st.button("Verwerk audio", key="process_audio_button", type="primary"):
            process_uploaded_audio(uploaded_file)
    st.markdown("</div>", unsafe_allow_html=True)

def render_multiple_audio_upload():
    st.markdown("<div class='info-container'>", unsafe_allow_html=True)
    st.markdown("<h4 class='section-subtitle'>Upload meerdere audiobestanden</h4>", unsafe_allow_html=True)
    st.markdown("<p class='info-text'>Upload meerdere audio- of videobestanden om te transcriberen. De transcripties worden samengevoegd in de volgorde van uploaden.</p>", unsafe_allow_html=True)
    uploaded_files = st.file_uploader("Kies bestanden", type=config.ALLOWED_AUDIO_TYPES, accept_multiple_files=True, key="multiple_audio_uploader")
    if uploaded_files:
        total_size = sum(file.size for file in uploaded_files)
        st.write(f"Aantal bestanden: {len(uploaded_files)}, Totale grootte: {total_size / 1024:.2f} KB")
        if st.button("Verwerk audiobestanden", key="process_multiple_audio_button", type="primary"):
            if len(uploaded_files) > 5:
                confirm = st.checkbox("Ik begrijp dat het verwerken van meerdere bestanden langer kan duren.")
                if confirm:
                    process_multiple_audio_files(uploaded_files)
            else:
                process_multiple_audio_files(uploaded_files)
    st.markdown("</div>", unsafe_allow_html=True)

def render_audio_recording():
    st.markdown("<div class='info-container'>", unsafe_allow_html=True)
    st.markdown("<h4 class='section-subtitle'>Neem audio op</h4>", unsafe_allow_html=True)
    st.markdown("<p class='info-text'>Neem uw gesprek direct op via uw microfoon. Zorg ervoor dat uw microfoon is ingeschakeld en geef toestemming in uw browser.</p>", unsafe_allow_html=True)
    st.markdown("<h5>Checklist voor het gesprek:</h5>", unsafe_allow_html=True)
    
    checklist_items = [
        ("Pensioendatum", "Bespreek de verwachte pensioendatum en gerelateerde plannen"),
        ("Arbeidsongeschiktheid", "Behandel scenario's en dekking bij arbeidsongeschiktheid"),
        ("Overlijden", "Bespreek regelingen en voorzieningen in geval van overlijden")
    ]
    
    for item, description in checklist_items:
        col1, col2 = st.columns([1, 10])
        with col1:
            st.checkbox("", key=f"checklist_{item.lower().replace(' ', '_')}")
        with col2:
            st.markdown(f"<div class='checklist-item'><strong>{item}</strong><span class='checklist-description'> - {description}</span></div>", unsafe_allow_html=True)
    
    audio_data = mic_recorder(key="audio_recorder", start_prompt="Start opname", stop_prompt="Stop opname", use_container_width=True)
    
    if audio_data is not None:
        if isinstance(audio_data, dict) and audio_data.get("state") == "recording":
            st.session_state.is_recording = True
            st.rerun()
        elif isinstance(audio_data, dict) and 'bytes' in audio_data:
            st.session_state.audio_data = audio_data
            process_recorded_audio(audio_data)
    st.markdown("</div>", unsafe_allow_html=True)

def render_text_input():
    st.markdown("<div class='info-container'>", unsafe_allow_html=True)
    st.markdown("<h4 class='section-subtitle'>Voer tekst in</h4>", unsafe_allow_html=True)
    st.markdown("<p class='info-text'>Schrijf of plak uw gespreksnotities hier. Probeer zo volledig mogelijk te zijn en gebruik interpunctie voor betere resultaten.</p>", unsafe_allow_html=True)
    st.session_state.input_text = st.text_area("Voer tekst in of plak tekst:", height=300, key="text_input_area")
    if st.button("Verwerk tekst", key="process_text_button"):
        if st.session_state.input_text:
            st.session_state.transcription_complete = True
            st.success("Tekst succesvol verwerkt!")
        else:
            st.warning("Voer eerst tekst in voordat u op 'Verwerk tekst' klikt.")
    st.markdown("</div>", unsafe_allow_html=True)

def render_text_file_upload():
    st.markdown("<div class='info-container'>", unsafe_allow_html=True)
    st.markdown("<h4 class='section-subtitle'>Upload een tekstbestand</h4>", unsafe_allow_html=True)
    st.markdown("<p class='info-text'>Upload een tekstbestand met uw gespreksnotities. Ondersteunde formaten: TXT, DOC, DOCX, PDF.</p>", unsafe_allow_html=True)
    uploaded_file = st.file_uploader("Kies een tekstbestand", type=config.ALLOWED_TEXT_TYPES, key="text_file_uploader")
    if uploaded_file:
        st.session_state.uploaded_text = uploaded_file
        file_details = {"Bestandsnaam": uploaded_file.name, "Bestandsgrootte": f"{uploaded_file.size / 1024:.2f} KB"}
        st.json(file_details)
        if st.button("Verwerk bestand", key="process_file_button"):
            process_uploaded_text(uploaded_file)
    st.markdown("</div>", unsafe_allow_html=True)

def render_recording_in_progress():
    st.markdown("<div class='info-container'>", unsafe_allow_html=True)
    st.markdown("<h4 class='section-subtitle'>Opname is bezig</h4>", unsafe_allow_html=True)
    st.markdown("<p class='info-text'>Uw audio wordt opgenomen. Spreek duidelijk en probeer achtergrondgeluiden te minimaliseren voor de beste resultaten.</p>", unsafe_allow_html=True)
    audio_data = mic_recorder(key="audio_recorder_in_progress", start_prompt="Start opname", stop_prompt="Stop opname", use_container_width=True)
    
    if audio_data is not None and isinstance(audio_data, dict) and 'bytes' in audio_data:
        st.session_state.is_recording = False
        st.session_state.audio_data = audio_data
        process_recorded_audio(audio_data)
        st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

def render_transcript_editor():
    st.markdown("<div class='info-container'>", unsafe_allow_html=True)
    st.markdown("<h3 class='section-subtitle'>Bewerk transcript</h3>", unsafe_allow_html=True)
    st.markdown("<p class='info-text'>Controleer en bewerk indien nodig het gegenereerde transcript. Corrigeer eventuele fouten en voeg interpunctie toe waar nodig.</p>", unsafe_allow_html=True)
    st.session_state.input_text = st.text_area("Transcript:", value=st.session_state.input_text, height=300, key="final_transcript")
    if st.button("Bevestig transcript", key="confirm_transcript_button"):
        st.success("Transcript bevestigd. U kunt nu doorgaan naar de volgende stap.")
    st.markdown("</div>", unsafe_allow_html=True)

def process_uploaded_audio(uploaded_file):
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
            st.error("Transcriptie is mislukt. Controleer het audiobestand en probeer het opnieuw.")

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
            st.error("Transcriptie is mislukt. Probeer opnieuw op te nemen met een betere geluidskwaliteit.")

def process_uploaded_text(uploaded_file):
    with st.spinner("Bestand wordt verwerkt..."):
        st.session_state.input_text = process_text_file(uploaded_file)
        if st.session_state.input_text:
            st.session_state.transcription_complete = True
            st.success("Bestand succesvol geüpload en verwerkt!")
            st.write("Transcript lengte:", len(st.session_state.input_text))
            st.write("Eerste 100 karakters van transcript:", st.session_state.input_text[:100])
        else:
            st.error("Verwerking is mislukt. Controleer of het bestand leesbaar is en probeer het opnieuw.")