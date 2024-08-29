import streamlit as st
from streamlit_antd.table import st_antd_table
from streamlit_antd.result import Action, st_antd_result
from streamlit_antd.cards import Item, st_antd_cards
from docx import Document
from io import BytesIO
import pyperclip
import pandas as pd

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
    <style>
    .main {
        background-color: #f0f8ff;
        color: #333;
        font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
    }
    .stButton>button {
        background-color: #4CAF50;
        color: white;
        border: none;
        padding: 12px 28px;
        text-align: center;
        text-decoration: none;
        display: inline-block;
        font-size: 16px;
        margin: 4px 2px;
        cursor: pointer;
        border-radius: 30px;
        transition: all 0.3s ease 0s;
        box-shadow: 0 8px 15px rgba(0, 0, 0, 0.1);
    }
    .stButton>button:hover {
        background-color: #45a049;
        box-shadow: 0 15px 20px rgba(46, 229, 157, 0.4);
        transform: translateY(-7px);
    }
    .summary-box {
        border: none;
        border-radius: 15px;
        padding: 25px;
        margin: 20px 0;
        background-color: #ffffff;
        box-shadow: 0 10px 30px rgba(0, 0, 0, 0.1);
        transition: all 0.3s ease;
    }
    .summary-box:hover {
        box-shadow: 0 15px 40px rgba(0, 0, 0, 0.15);
        transform: translateY(-5px);
    }
    .summary-box h3 {
        color: #2c3e50;
        border-bottom: 2px solid #3498db;
        padding-bottom: 10px;
        margin-bottom: 20px;
        text-align: center;
        font-weight: 600;
    }
    .content {
        white-space: pre-wrap;
        word-wrap: break-word;
        font-size: 16px;
        line-height: 1.8;
        color: #34495e;
    }
    </style>
    """, unsafe_allow_html=True)