import streamlit as st
from speechmatics.models import ConnectionSettings
from speechmatics.batch_client import BatchClient
from httpx import HTTPStatusError
import os
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from langchain_core.output_parsers import StrOutputParser

# Initialization of page in session state
if 'page' not in st.session_state:
    st.session_state['page'] = 1
if 'sub_department' not in st.session_state:
    st.session_state['sub_department'] = None

# Function to load the prompt
def load_prompt(department):
    prompt_file_path = f'prompts/{department.lower()}.txt'
    try:
        with open(prompt_file_path, 'r', encoding='utf-8') as file:
            prompt_text = file.read()
            st.write("Prompt found, yay!")
            return prompt_text
    except FileNotFoundError:
        st.write("Prompt not found (error)")
        return ""

# Function to generate the summary
def generate_response(txt, speaker1, speaker2, subject, department, sub_department, openai_api_key):
    department_prompt = load_prompt(department)
    full_prompt = f"{department_prompt}\n\n### Transcript Information:\n" + \
                  f"- **Transcript**: {txt}\n- **Speaker 1**: {speaker1}\n- **Speaker 2**: {speaker2}\n- **Subject**: {subject}\n\n" + \
                  "### Conversation Summary:\n...\n\n### Action Points:\n...\n\n### End of Summary:"
    
    prompt_template = ChatPromptTemplate.from_template(full_prompt)
    model = ChatOpenAI(api_key=openai_api_key, model_name="gpt-4-turbo-preview", temperature=0.20)
    chain = prompt_template | model | StrOutputParser()
    summary = chain.invoke({"transcript": txt, "speaker1": speaker1, "speaker2": speaker2, "subject": subject})
    return summary

# Page for selecting the department
def department_selection_page():
    st.title('Choose your department')
    department = st.selectbox("Select the department:", ["Claims Handler", "Private Clients", "Businesses", "Financial Planning"])
    sub_department = None
    if department == "Financial Planning":
        sub_department = st.selectbox("Select the sub-department:", ["Pension", "Collective", "Income", "Planning", "Mortgage"])
    if st.button("Proceed to transcription"):
        st.session_state['department'] = department
        st.session_state['sub_department'] = sub_department
        st.session_state['page'] = 2

# Page for uploading files and direct text input
def upload_page():
    st.title('VA Conversation Summarizer')
    uploaded_file = st.file_uploader("Choose an MP3 file", type="mp3")
    if uploaded_file is not None:
        temp_dir = "temp"
        os.makedirs(temp_dir, exist_ok=True)
        temp_path = os.path.join(temp_dir, uploaded_file.name)
        with open(temp_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        st.session_state['uploaded_file_path'] = temp_path
        st.session_state['page'] = 1.5
    if st.button("Or paste your text here instead of uploading an MP3", key="paste_text"):
        st.session_state['page'] = 4

# Page for direct text input
def text_input_page():
    st.title("Text for Summarization")
    direct_text = st.text_area("Paste the text here", '', height=300)
    if st.button('Proceed to department selection', key='continue_to_department_selection'):
        st.session_state['direct_text'] = direct_text
        st.session_state['page'] = 1.5

# Page for transcription and editing
def transcription_page():
    st.title("Transcribing and Editing")
    if 'uploaded_file_path' in st.session_state and st.session_state['uploaded_file_path']:
        temp_path = st.session_state['uploaded_file_path']
        if st.button('Transcribe', key='transcribe_audio'):
            AUTH_TOKEN = st.secrets["speechmatics"]["auth_token"]
            LANGUAGE = "nl"
            settings = ConnectionSettings(
                url="https://asr.api.speechmatics.com/v2",
                auth_token=AUTH_TOKEN,
            )
            conf = {
                "type": "transcription",
                "transcription_config": {
                    "language": LANGUAGE,
                    "operating_point": "enhanced",
                    "diarization": "speaker",
                    "speaker_diarization_config": {
                        "speaker_sensitivity": 0.2
                    }
                },
            }
            with BatchClient(settings) as speech_client:
                try:
                    job_id = speech_client.submit_job(audio=temp_path, transcription_config=conf)
                    st.session_state['transcript'] = speech_client.wait_for_completion(job_id, transcription_format="txt")
                except HTTPStatusError as e:
                    st.error(f"Error during transcription: {str(e)}")
                    return
            os.remove(temp_path)

        if 'transcript' in st.session_state:
            edited_text = st.text_area("Edit Transcript", st.session_state['transcript'], height=300)
            speaker1 = st.text_input("Name of Speaker 1 (S1)")
            speaker2 = st.text_input("Name of Speaker 2 (S2)")
            subject = st.text_input("Subject of the Conversation")
            if st.button('Proceed to Summary', key='continue_to_summary'):
                st.session_state['edited_text'] = edited_text
                st.session_state['speaker1'] = speaker1
                st.session_state['speaker2'] = speaker2
                st.session_state['subject'] = subject
                st.session_state['page'] = 3

# Page for summary
def summary_page():
    st.title("Conversation Summary")
    text_to_summarize = st.session_state.get('direct_text') or st.session_state.get('edited_text', '')
    if text_to_summarize and 'speaker1' in st.session_state and 'speaker2' in st.session_state and 'subject' in st.session_state and 'department' in st.session_state:
        summary = generate_response(
            text_to_summarize,
            st.session_state['speaker1'],
            st.session_state['speaker2'],
            st.session_state['subject'],
            st.session_state['department'],
            st.session_state['sub_department'],
            st.secrets["openai"]["api_key"]
        )
        st.text_area("Summary", summary, height=150)

# Page navigation
if st.session_state['page'] == 1:
    upload_page()
elif st.session_state['page'] == 4:
    text_input_page()
elif st.session_state['page'] == 1.5:
    department_selection_page()
elif st.session_state['page'] == 2:
    transcription_page()
elif st.session_state['page'] == 3:
    summary_page()
