import streamlit as st
from pydub import AudioSegment
import tempfile
from utils.api_calls import get_openai_client
from streamlit_mic_recorder import mic_recorder
import os
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Initialize session state variables
if 'processing_complete' not in st.session_state:
    st.session_state['processing_complete'] = False
if 'transcription_done' not in st.session_state:
    st.session_state['transcription_done'] = False
if 'transcript' not in st.session_state:
    st.session_state['transcript'] = ""

def split_audio(file_path, max_duration_ms=30000):
    logger.debug(f"Attempting to load audio file: {file_path}")
    try:
        audio = AudioSegment.from_file(file_path)
        logger.debug(f"Audio file loaded successfully. Duration: {len(audio)}ms")
        chunks = []
        for i in range(0, len(audio), max_duration_ms):
            chunk = audio[i:i+max_duration_ms]
            logger.debug(f"Created chunk {len(chunks)}: {len(chunk)}ms")
            chunks.append(chunk)
        logger.debug(f"Split audio into {len(chunks)} chunks")
        return chunks
    except Exception as e:
        logger.error(f"Error splitting audio: {str(e)}", exc_info=True)
        raise

def transcribe_audio(file_path):
    transcript_text = ""
    logger.debug(f"Starting transcription for file: {file_path}")
    with st.spinner('Audio segmentatie wordt gestart...'):
        try:
            audio_segments = split_audio(file_path)
        except Exception as e:
            logger.error(f"Fout bij het segmenteren van het audio: {str(e)}", exc_info=True)
            return "Segmentatie mislukt."

    total_segments = len(audio_segments)
    progress_bar = st.progress(0)
    progress_text = st.empty()
    progress_text.text("Start transcriptie...")
    for i, segment in enumerate(audio_segments):
        progress_text.text(f'Bezig met verwerken van segment {i+1} van {total_segments} - {((i+1)/total_segments*100):.2f}% voltooid')
        with tempfile.NamedTemporaryFile(delete=True, suffix='.wav') as temp_file:
            logger.debug(f"Exporting segment {i+1} to temporary file: {temp_file.name}")
            segment.export(temp_file.name, format="wav")
            with open(temp_file.name, "rb") as audio_file:
                try:
                    client = get_openai_client()
                    logger.debug(f"Sending segment {i+1} to OpenAI for transcription")
                    transcription_response = client.audio.transcriptions.create(file=audio_file, model="whisper-1")
                    if hasattr(transcription_response, 'text'):
                        transcript_text += transcription_response.text + " "
                        logger.debug(f"Transcription received for segment {i+1}")
                    else:
                        logger.warning(f"Unexpected response format for segment {i+1}")
                except Exception as e:
                    logger.error(f"Fout bij het transcriberen van segment {i+1}: {str(e)}", exc_info=True)
                    continue
        progress_bar.progress((i + 1) / total_segments)
    progress_text.success("Transcriptie voltooid.")
    logger.debug("Full transcription completed")
    return transcript_text.strip()

def process_audio_input(input_method):
    logger.debug(f"Processing audio input with method: {input_method}")
    if not st.session_state.get('processing_complete', False):
        if input_method == "Upload audio":
            uploaded_file = st.file_uploader("Upload an audio file", type=['wav', 'mp3', 'mp4', 'm4a', 'ogg', 'webm'])
            if uploaded_file is not None and not st.session_state.get('transcription_done', False):
                logger.debug(f"Audio file uploaded: {uploaded_file.name}")
                with st.spinner("Transcriberen van audio..."):
                    with tempfile.NamedTemporaryFile(delete=False, suffix="." + uploaded_file.name.split('.')[-1]) as tmp_audio:
                        tmp_audio.write(uploaded_file.getvalue())
                        tmp_audio.flush()
                        logger.debug(f"Temporary file created: {tmp_audio.name}")
                        st.session_state['transcript'] = transcribe_audio(tmp_audio.name)
                    os.unlink(tmp_audio.name)
                    logger.debug(f"Temporary file deleted: {tmp_audio.name}")
                st.session_state['transcription_done'] = True
                st.rerun()
        elif input_method == "Neem audio op":
            audio_data = mic_recorder(key="recorder", start_prompt="Start opname", stop_prompt="Stop opname", use_container_width=True, format="webm")
            if audio_data and 'bytes' in audio_data and not st.session_state.get('transcription_done', False):
                logger.debug("Audio recorded successfully")
                with st.spinner("Transcriberen van audio..."):
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".webm") as tmp_audio:
                        tmp_audio.write(audio_data['bytes'])
                        tmp_audio.flush()
                        logger.debug(f"Temporary file created for recorded audio: {tmp_audio.name}")
                        st.session_state['transcript'] = transcribe_audio(tmp_audio.name)
                    os.unlink(tmp_audio.name)
                    logger.debug(f"Temporary file deleted: {tmp_audio.name}")
                st.session_state['transcription_done'] = True
                st.rerun()
        
        

if 'processing_complete' not in st.session_state:
    st.session_state['processing_complete'] = False
if 'transcription_done' not in st.session_state:
    st.session_state['transcription_done'] = False
if 'transcript' not in st.session_state:
    st.session_state['transcript'] = ""

def main():
    st.title("Klantuitvraagtool")

    # Input Section
    st.header("Input Section")
    input_method = st.radio("Kies de invoermethode", ["Upload audio", "Neem audio op"])

    try:
        process_audio_input(input_method)
    except Exception as e:
        logger.error(f"Error in audio processing: {str(e)}", exc_info=True)
        st.error(f"An error occurred during audio processing: {str(e)}")

    # Display transcription result
    if st.session_state['transcription_done']:
        st.header("Transcriptie Resultaat")
        transcript = st.session_state['transcript']
        st.text_area("Transcriptie", transcript, height=300)

    # Add a debug section
    st.header("Debug Information")
    st.write(f"Processing complete: {st.session_state['processing_complete']}")
    st.write(f"Transcription done: {st.session_state['transcription_done']}")
    st.write(f"Transcript length: {len(st.session_state['transcript'])}")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logger.error(f"Unhandled exception in main: {str(e)}", exc_info=True)
        st.error(f"An unexpected error occurred: {str(e)}")