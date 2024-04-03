import streamlit as st
from langchain import LangChain
from streamlit_audio_recorder import st_audio_recorder
import openai
import tempfile
from pydub import AudioSegment
import soundfile as sf

# Initialize LangChain (assuming appropriate setup)
lc = LangChain()

# Whisper model loading for transcription (assuming local or cloud model setup)
def transcribe_audio(audio_file):
    audio = AudioSegment.from_file(audio_file)
    audio.export("temp.wav", format="wav")
    # Adjust the path to the Whisper model if it's hosted or specify the model size
    transcript = lc.transcribe("temp.wav")
    return transcript

# GPT-4 Turbo summarization function
def summarize_text(text, department):
    prompt = f"Summarize the following text for the {department} department:\n\n{text}"
    response = openai.Completion.create(
        model="gpt-4-turbo",
        prompt=prompt,
        temperature=0.5,
        max_tokens=100,
    )
    return response.choices[0].text.strip()

# Streamlit app UI
def main():
    st.title("Insurance Dossier Summarizer")

    department = st.selectbox("Select Your Department", ["Insurance", "Financial Advice", "Claims", "Customer Service"])

    input_method = st.radio("Choose input method:", ["Upload Text", "Upload Audio", "Paste Text", "Type Directly", "Record"])

    if input_method == "Upload Text":
        uploaded_file = st.file_uploader("Choose a file")
        if uploaded_file is not None:
            text = uploaded_file.getvalue().decode("utf-8")
            summary = summarize_text(text, department)
            st.text_area("Summary", value=summary, height=250)

    elif input_method == "Upload Audio":
        uploaded_file = st.file_uploader("Choose an audio file", type=["mp3", "wav"])
        if uploaded_file is not None:
            with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
                tmp_file.write(uploaded_file.read())
                transcript = transcribe_audio(tmp_file.name)
                summary = summarize_text(transcript, department)
                st.text_area("Transcript", value=transcript, height=250)
                st.text_area("Summary", value=summary, height=250)

    elif input_method == "Paste Text":
        text = st.text_area("Paste text here:")
        if st.button("Summarize"):
            summary = summarize_text(text, department)
            st.text_area("Summary", value=summary, height=250)

    elif input_method == "Type Directly":
        text = st.text_area("Type text here:")
        if st.button("Summarize"):
            summary = summarize_text(text, department)
            st.text_area("Summary", value=summary, height=250)

    elif input_method == "Record":
        audio_data = st_audio_recorder(rec_time=300, display_chunk=True)
        if audio_data is not None:
            audio_bytes = audio_data.audio_bytes
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_file:
                tmp_file.write(audio_bytes)
                transcript = transcribe_audio(tmp_file.name)
                summary = summarize_text(transcript, department)
                st.text_area("Transcript", value=transcript, height=250)
                st.text_area("Summary", value=summary, height=250)

if __name__ == "__main__":
    main()
