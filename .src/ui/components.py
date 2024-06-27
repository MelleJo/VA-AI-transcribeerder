import streamlit as st
import html

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
    .transcript-box {
        border: none;
        border-radius: 10px;
        padding: 15px;
        margin-bottom: 20px;
        background-color: #f9f9f9;
        box-shadow: 0 5px 15px rgba(0, 0, 0, 0.05);
    }
    .copy-button {
        text-align: center;
        margin-top: 20px;
    }
    .stProgress > div > div > div > div {
        background-color: #3498db;
    }
    .stSelectbox {
        color: #2c3e50;
    }
    .stSelectbox > div > div {
        background-color: #ffffff;
        border-radius: 5px;
    }
    .stRadio > div {
        background-color: #ffffff;
        border-radius: 5px;
        padding: 10px;
        box-shadow: 0 2px 5px rgba(0, 0, 0, 0.05);
    }
    </style>
    """, unsafe_allow_html=True)

def display_transcript(transcript):
    if transcript:
        with st.expander("Toon Transcript", expanded=False):
            st.markdown('<div class="transcript-box">', unsafe_allow_html=True)
            st.markdown('<h4>Transcript</h4>', unsafe_allow_html=True)
            st.markdown(f'<div class="content">{html.escape(transcript)}</div>', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)

def display_summary(summary):
    if summary:
        st.markdown('<div class="summary-box">', unsafe_allow_html=True)
        st.markdown('<h3>Samenvatting</h3>', unsafe_allow_html=True)
        st.markdown(summary, unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

def display_department_selector(departments):
    return st.selectbox("Kies je afdeling", departments, key='department_select')

def display_input_method_selector(input_methods):
    return st.radio("Wat wil je laten samenvatten?", input_methods, key='input_method_radio')

def display_text_input():
    return st.text_area("Voeg tekst hier in:", 
                        value=st.session_state.get('input_text', ''), 
                        height=300,
                        key='input_text_area')

def display_file_uploader(file_types):
    return st.file_uploader("Choose a file", type=file_types)

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