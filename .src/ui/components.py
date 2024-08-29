import streamlit as st
from streamlit_antd.table import st_antd_table
from streamlit_antd.result import Action, st_antd_result
from streamlit_antd.cards import Item, st_antd_cards
from docx import Document
from io import BytesIO
import pyperclip
import pandas as pd

def initialize_session_state():
    defaults = {
        'summary': "",
        'summary_versions': [],
        'current_version_index': -1,
        'business_side': "",
        'department': "",
        'prompt': "",
        'input_method': "",
        'input_text': "",
        'transcript': "",
        'gesprekslog': [],
        'product_info': "",
        'selected_products': [],
        'transcription_done': False,
        'summarization_done': False,
        'processing_complete': False,
        'current_step': 0,
        'user_name': "",
        'PROMPTS_DIR': "",
        'QUESTIONS_DIR': "",
        'BUSINESS_SIDES': [],
        'DEPARTMENTS': {},
        'INPUT_METHODS': []
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

def display_transcript(transcript):
    if transcript:
        st_antd_table(pd.DataFrame({"Transcript": [transcript]}), color_background="#f9f6f1")

def display_summary(summary):
    if summary:
        sections = summary.split('\n\n')
        
        # Display header information
        if sections:
            header_lines = sections[0].split('\n')
            title = header_lines[0] if header_lines else 'Summary'
            sub_title = "\n".join(header_lines[1:]) if len(header_lines) > 1 else ""
            
            actions = [
                Action("download", "Download als Word"),
                Action("copy", "Kopieer naar klembord")
            ]
            
            clicked_event = st_antd_result(title, sub_title, actions)
            
            if clicked_event:
                if clicked_event["action"] == "download":
                    doc = create_word_document(summary)
                    st.download_button(
                        label="Download Word bestand",
                        data=doc,
                        file_name="samenvatting.docx",
                        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                    )
                elif clicked_event["action"] == "copy":
                    pyperclip.copy(summary)
                    st.success("Samenvatting gekopieerd naar klembord!")
        
        # Display main content
        for section in sections[1:]:
            st.markdown(section)
    else:
        st.warning("No summary available.")

def create_word_document(content):
    doc = Document()
    doc.add_paragraph(content)
    doc_io = BytesIO()
    doc.save(doc_io)
    doc_io.seek(0)
    return doc_io.read()

def display_text_input(label, value="", height=100):
    return st.text_area(label, value=value, height=height)

def display_file_uploader(label, type=None):
    return st.file_uploader(label, type=type)

def setup_page_style():
    st.set_page_config(page_title="Gesprekssamenvatter", page_icon="🎙️", layout="wide")
    st.markdown("""
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0-beta3/css/all.min.css">
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Roboto:wght@300;400;700&display=swap');

    body {
        font-family: 'Roboto', sans-serif;
        background-color: #f0f4f8;
        color: #1a202c;
    }
    .main {
        padding: 2rem;
    }
    h1, h2, h3 {
        color: #2d3748;
    }
    .stButton>button {
        background-color: #4299e1;
        color: white;
        border: none;
        padding: 0.75rem 1.5rem;
        border-radius: 0.375rem;
        font-weight: 600;
        transition: background-color 0.3s ease, transform 0.3s ease;
    }
    .stButton>button:hover {
        background-color: #2c5282;
        transform: translateY(-3px);
    }
    .ant-card {
        border-radius: 0.5rem;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        transition: all 0.3s ease;
        cursor: pointer;
    }
    .ant-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 8px 15px rgba(0, 0, 0, 0.1);
    }
    .ant-card-head-title {
        font-weight: 700;
        color: #2d3748;
    }
    .ant-card-body {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        text-align: center;
        padding: 1.5rem;
    }
    .ant-card i {
        font-size: 2.5rem;
        margin-bottom: 1rem;
        color: #4299e1;
    }
    .ant-card-meta-description {
        color: #718096;
    }
    </style>
    """, unsafe_allow_html=True)
