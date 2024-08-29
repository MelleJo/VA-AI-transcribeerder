import os
import pytz
from datetime import datetime
import streamlit as st
import pyperclip

PROMPTS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'prompts'))
QUESTIONS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'questions'))

import os
from config import load_config

# Load configurations from config.py
config = load_config()


def get_local_time():
    timezone = pytz.timezone("Europe/Amsterdam")
    return datetime.now(timezone).strftime('%d-%m-%Y %H:%M:%S')

# text_processing.py

import os
from config import load_config

# Load configurations from config.py
config = load_config()

import os
from config import load_config

# Load configurations from config.py
config = load_config()

def load_prompt(file_name):
    # Construct the path based on the file name directly
    path = os.path.join(config['PROMPTS_DIR'], file_name)
    
    # Log the full path
    st.write(f"Loading prompt file from: {path}")
    
    # Check if the path exists and is a file
    if not os.path.exists(path) or not os.path.isfile(path):
        st.error(f"Bestand niet gevonden: {path}")
        raise FileNotFoundError(f"Bestand niet gevonden: {path}")
    
    # Load and return the prompt content
    with open(path, "r", encoding="utf-8") as file:
        return file.read()




def load_questions(file_name):
    path = os.path.join(QUESTIONS_DIR, file_name)
    if not os.path.exists(path):
        st.error(f"Bestand niet gevonden: {path}")
        raise FileNotFoundError(f"Bestand niet gevonden: {path}")
    with open(path, "r", encoding="utf-8") as file:
        return file.readlines()

def update_gesprekslog(transcript, summary):
    current_time = get_local_time()
    if 'gesprekslog' not in st.session_state:
        st.session_state['gesprekslog'] = []
    st.session_state['gesprekslog'].insert(0, {'time': current_time, 'transcript': transcript, 'summary': summary})
    st.session_state['gesprekslog'] = st.session_state['gesprekslog'][:5]

def copy_to_clipboard(text):
    pyperclip.copy(text)
    st.success("Gekopieerd naar klembord!")