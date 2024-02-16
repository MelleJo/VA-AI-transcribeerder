import streamlit as st
from speechmatics.models import ConnectionSettings
from speechmatics.batch_client import BatchClient
from httpx import HTTPStatusError
import os
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from langchain_core.output_parsers import StrOutputParser

# Initialization of page and department in session state if not already present
if 'page' not in st.session_state:
    st.session_state.page = 1
if 'sub_department' not in st.session_state:
    st.session_state.sub_department = None

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
    proceed = st.button("Proceed to summary")
    if proceed:
        st.session_state.department = department
        st.session_state.sub_department = sub_department
        st.session_state.page = 3  # Directly move to summary page after department selection

# Page for uploading files and direct text input
def upload_page():
    st.title('VA Conversation Summarizer')
    uploaded_file = st.file_uploader("Choose an MP3 file", type="mp3")
    proceed_to_transcription = st.button("Proceed to transcription")
    if uploaded_file is not None and proceed_to_transcription:
        temp_dir = "temp"
        os.makedirs(temp_dir, exist_ok=True)
        temp_path = os.path.join(temp_dir, uploaded_file.name)
        with open(temp_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        st.session_state.uploaded_file_path = temp_path
        st.session_state.page = 1.5  # Move to department selection before transcription

    paste_text = st.button("Or paste your text here instead of uploading an MP3")
    if paste_text:
        st.session_state.page = 4  # Move directly to text input page

# Page for direct text input
def text_input_page():
    st.title("Text for Summarization")
    direct_text = st.text_area("Paste the text here", '', height=300)
    submit_text = st.button('Submit text')
    if submit_text:
        st.session_state.direct_text = direct_text
        st.session_state.page = 1.5  # Move to department selection after submitting text

# Page for summary
def summary_page():
    st.title("Conversation Summary")
    text_to_summarize = st.session_state.get('direct_text', '')
    if text_to_summarize and 'department' in st.session_state:
        # Assuming default values for speaker1, speaker2, and subject for direct text summarization
        summary = generate_response(
            text_to_summarize,
            "Speaker 1",
            "Speaker 2",
            "Subject",
            st.session_state.department,
            st.session_state.sub_department,
            st.secrets["openai"]["api_key"]
        )
        st.text_area("Summary", summary, height=150)

# Page navigation logic
if st.session_state.page == 1:
    upload_page()
elif st.session_state.page == 4:
    text_input_page()
elif st.session_state.page == 1.5:
    department_selection_page()
elif st.session_state.page == 3:
    summary_page()
