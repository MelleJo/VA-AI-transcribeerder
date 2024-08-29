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

def display_department_selector(departments):
    items = [Item(id=dept, title=dept) for dept in departments]
    event = st_antd_cards(items, key="department_selector")
    if event:
        return event["payload"]["id"]
    return None

def display_input_method_selector(input_methods):
    items = [Item(id=method, title=method) for method in input_methods]
    event = st_antd_cards(items, key="input_method_selector")
    if event:
        return event["payload"]["id"]
    return None

def display_summarize_button():
    return st.button("Samenvatten", key='summarize_button')

def display_copy_clipboard_button():
    return st.button("Kopieer naar klembord", key='copy_clipboard_button')

def display_progress_bar():
    return st.progress(0)

def display_spinner(text):
    return st.spinner(text)

def display_success(text):
    st.success(text)

def display_error(text):
    st.error(text)

def display_warning(text):
    st.warning(text)

def setup_page_style():
    st.set_page_config(page_title="Gesprekssamenvatter", page_icon="🎙️", layout="wide")
    st.markdown("""
    <link href="https://fonts.googleapis.com/css2?family=Roboto:wght@300;400;700&display=swap" rel="stylesheet">
    <style>
    body {
        font-family: 'Roboto', sans-serif;
        background-color: #f0f2f6;
        color: #1e1e1e;
    }
    .stApp {
        max-width: 1200px;
        margin: 0 auto;
    }
    h1 {
        color: #2c3e50;
        font-weight: 700;
        font-size: 2.5rem;
        margin-bottom: 1rem;
    }
    h2 {
        color: #34495e;
        font-weight: 400;
        font-size: 1.8rem;
        margin-bottom: 0.5rem;
    }
    .stButton>button {
        background-color: #3498db;
        color: white;
        border: none;
        padding: 0.5rem 1rem;
        font-size: 1rem;
        font-weight: 500;
        border-radius: 5px;
        transition: all 0.3s ease;
    }
    .stButton>button:hover {
        background-color: #2980b9;
        box-shadow: 0 4px 8px rgba(0,0,0,0.1);
    }
    .card-container {
        display: flex;
        flex-wrap: wrap;
        justify-content: center;
        gap: 1rem;
        margin-top: 1rem;
    }
    .card {
        background-color: white;
        border-radius: 10px;
        padding: 1.5rem;
        width: 200px;
        text-align: center;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        transition: all 0.3s ease;
        cursor: pointer;
    }
    .card:hover {
        transform: translateY(-5px);
        box-shadow: 0 6px 12px rgba(0,0,0,0.15);
    }
    .card-icon {
        font-size: 3rem;
        margin-bottom: 1rem;
        color: #3498db;
    }
    .card-title {
        font-size: 1.2rem;
        font-weight: 500;
        margin-bottom: 0.5rem;
    }
    .card-description {
        font-size: 0.9rem;
        color: #7f8c8d;
    }
    .stTextInput>div>div>input {
        background-color: white;
        border: 1px solid #bdc3c7;
        border-radius: 5px;
        padding: 0.5rem;
        font-size: 1rem;
    }
    .stTextInput>label {
        font-size: 1rem;
        font-weight: 500;
        color: #34495e;
    }
    </style>
    """, unsafe_allow_html=True)