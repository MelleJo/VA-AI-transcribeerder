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
        st.dataframe(pd.DataFrame({"Transcript": [transcript]}), use_container_width=True)

def display_summary(summary):
    if summary:
        st.markdown(summary)
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Download als Word"):
                doc = create_word_document(summary)
                st.download_button(
                    label="Download Word bestand",
                    data=doc,
                    file_name="samenvatting.docx",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                )
        with col2:
            if st.button("Kopieer naar klembord"):
                try:
                    st.write("Samenvatting gekopieerd naar klembord!")
                except:
                    st.error("Kon niet kopiëren naar klembord. Kopieer de tekst handmatig.")

def create_word_document(content):
    from docx import Document
    from io import BytesIO
    
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
