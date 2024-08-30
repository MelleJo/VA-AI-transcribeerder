# src/config.py

import streamlit as st
import os

# API Configuration
OPENAI_API_KEY = st.secrets["OPENAI_API_KEY"]

# Input Configuration
ALLOWED_AUDIO_TYPES = ["mp3", "wav", "ogg"]
ALLOWED_TEXT_TYPES = ["txt", "pdf", "docx"]

# Prompt Configuration
PROMPTS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "prompts")

# UI Configuration
THEME_COLOR = "#3B82F6"

# AI Configuration
AUDIO_MODEL = "whisper-1"
SUMMARY_MODEL = "gpt-4"
MAX_TOKENS = 1000
TEMPERATURE = 0.5
AUDIO_SEGMENT_LENGTH = 30000  # 30 seconds in milliseconds