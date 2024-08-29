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
    <style>
    .stButton>button {
        background-color: #4CAF50;
        color: white;
        padding: 10px 20px;
        border: none;
        border-radius: 5px;
        cursor: pointer;
        font-size: 16px;
    }
    .stButton>button:hover {
        background-color: #45a049;
    }
    .stTextArea>div>div>textarea {
        font-size: 16px;
    }
    </style>
    """, unsafe_allow_html=True)
