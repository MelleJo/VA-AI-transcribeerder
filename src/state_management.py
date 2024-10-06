# src/state_management.py

import streamlit as st
from enum import Enum, auto
import logging

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
    if 'summaries' not in st.session_state:
        st.session_state.summaries = []
    if 'current_version' not in st.session_state:
        st.session_state.current_version = 0

def transition_to_input_selection():
    st.session_state.state = AppState.INPUT_SELECTION
    logger.info("Transitioned to INPUT_SELECTION state")

def transition_to_processing(input_text):
    st.session_state.input_text = input_text
    st.session_state.state = AppState.PROCESSING
    logger.info("Transitioned to PROCESSING state")

def transition_to_results(summary):
    st.session_state.summary = summary
    st.session_state.summaries.append(summary)
    st.session_state.current_version = len(st.session_state.summaries) - 1
    st.session_state.state = AppState.RESULTS
    logger.info("Transitioned to RESULTS state")

def reset_state():
    st.session_state.state = AppState.PROMPT_SELECTION
    st.session_state.selected_prompt = None
    st.session_state.input_text = ""
    st.session_state.summary = ""
    st.session_state.summaries = []
    st.session_state.current_version = 0
    logger.info("Reset application state")