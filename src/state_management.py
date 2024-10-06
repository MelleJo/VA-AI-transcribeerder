# src/state_management.py

import streamlit as st
from enum import Enum, auto
import logging
from src.utils import load_prompts

logger = logging.getLogger(__name__)

class AppState(Enum):
    PROMPT_SELECTION = auto()
    INPUT_SELECTION = auto()
    PROCESSING = auto()
    RESULTS = auto()

def initialize_session_state():
    if 'state' not in st.session_state:
        st.session_state.state = AppState.PROMPT_SELECTION
    if 'selected_prompt' not in st.session_state:
        st.session_state.selected_prompt = None
    if 'input_text' not in st.session_state:
        st.session_state.input_text = ""
    if 'summary' not in st.session_state:
        st.session_state.summary = ""
    if 'processing_complete' not in st.session_state:
        st.session_state.processing_complete = False
    if 'base_prompt' not in st.session_state:
        prompts = load_prompts()
        st.session_state.base_prompt = prompts.get('base_prompt.txt', '')

def transition_to_next_state():
    current_state = st.session_state.state
    if current_state == AppState.PROMPT_SELECTION:
        st.session_state.state = AppState.INPUT_SELECTION
    elif current_state == AppState.INPUT_SELECTION:
        st.session_state.state = AppState.PROCESSING
    elif current_state == AppState.PROCESSING:
        st.session_state.state = AppState.RESULTS
    logger.info(f"Transitioned from {current_state} to {st.session_state.state}")

def reset_state():
    st.session_state.state = AppState.PROMPT_SELECTION
    st.session_state.selected_prompt = None
    st.session_state.input_text = ""
    st.session_state.summary = ""
    st.session_state.processing_complete = False
    logger.info("Reset application state")