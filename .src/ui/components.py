import streamlit as st

def setup_page_style():
    st.markdown("""
    <style>
    .stApp {
        background-color: #ffffff;
    }
    .stButton>button {
        width: 100%;
        height: 3em;
        background-color: #4CAF50;
        color: white;
        border: none;
        border-radius: 5px;
        font-size: 16px;
    }
    .stButton>button:hover {
        background-color: #45a049;
    }
    .stProgress > div > div > div > div {
        background-color: #4CAF50;
    }
    </style>
    """, unsafe_allow_html=True)

def initialize_session_state(config):
    defaults = {
        'summary': "",
        'summary_versions': [],
        'current_version_index': -1,
        'prompt_name': "",
        'prompt_path': "",
        'input_method': "",
        'input_text': "",
        'transcript': "",
        'gesprekslog': [],
        'current_step': 0,
        'user_name': "",
        'config': config
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

def display_text_input(label, value="", height=100):
    return st.text_area(label, value=value, height=height)

def display_file_uploader(label, type=None):
    return st.file_uploader(label, type=type)

def display_audio_recorder():
    # Implement audio recording functionality
    pass
