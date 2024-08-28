import os
import pytz
from datetime import datetime
import streamlit as st
import pyperclip

PROMPTS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'prompts'))

def get_local_time():
    timezone = pytz.timezone("Europe/Amsterdam")
    return datetime.now(timezone).strftime('%d-%m-%Y %H:%M:%S')

def load_prompt(file_name):
    path = os.path.join(PROMPTS_DIR, file_name)
    if not os.path.exists(path):
        st.error(f"Bestand niet gevonden: {path}")
        raise FileNotFoundError(f"Bestand niet gevonden: {path}")
    with open(path, "r", encoding="utf-8") as file:
        return file.read()

def update_gesprekslog(transcript, summary):
    current_time = get_local_time()
    if 'gesprekslog' not in st.session_state:
        st.session_state['gesprekslog'] = []
    st.session_state['gesprekslog'].insert(0, {'time': current_time, 'transcript': transcript, 'summary': summary})
    st.session_state['gesprekslog'] = st.session_state['gesprekslog'][:5]

def copy_to_clipboard(text):
    pyperclip.copy(text)
    st.success("Gekopieerd naar klembord!")