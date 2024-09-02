# src/config.py

import streamlit as st
import os

# API Configuration
OPENAI_API_KEY = st.secrets["OPENAI_API_KEY"]

# Input Configuration
ALLOWED_AUDIO_TYPES = ["mp3", "wav", "ogg", "m4a"]
ALLOWED_TEXT_TYPES = ["txt", "pdf", "docx"]

# Prompt Configuration
PROMPTS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "prompts")

# UI Configuration
THEME_COLOR = "#3B82F6"

# AI Configuration
AUDIO_MODEL = "whisper-1"
SUMMARY_MODEL = "gpt-4o-2024-08-06"
MAX_TOKENS = 10000
TEMPERATURE = 0.1
AUDIO_SEGMENT_LENGTH = 30000  # 30 seconds in milliseconds