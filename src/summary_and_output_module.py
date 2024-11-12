import os
import streamlit as st
import logging
from openai import OpenAI
from src.config import SUMMARY_MODEL, MAX_TOKENS, TEMPERATURE, TOP_P, FREQUENCY_PENALTY, PRESENCE_PENALTY, get_colleague_emails
from src.history_module import add_to_history
from src.utils import load_prompts, get_prompt_content
from src.utils import post_process_grammar_check, format_currency
from datetime import datetime
import base64
import io
from docx import Document
from docx.shared import Pt, RGBColor
from docx.enum.style import WD_STYLE_TYPE
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_JUSTIFY
from reportlab.lib.colors import darkblue, black
import markdown2
import re
from src.ui_components import ui_card, ui_button, ui_download_button, ui_copy_button, full_screen_loader, add_loader_css, estimate_time
import smtplib
from email.mime.text import MIMEText
from st_copy_to_clipboard import st_copy_to_clipboard
from email.mime.multipart import MIMEMultipart
import uuid
import time
import pandas as pd
from src.state_utils import convert_summaries_to_dict_format
from src.email_module import send_email
from src.enhanced_summary_module import generate_enhanced_summary  # Ensure this import is present
from src.input_module import transcribe_with_progress  # Assuming this function exists for transcription

logger = logging.getLogger(__name__)
client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

def load_css():
    return """
    <style>
    .stButton > button {
        background-color: #f0f2f6;
        color: #000000;
        border: 1px solid #d1d5db;
        border-radius: 4px;
        padding: 0.5rem 1rem;
        font-size: 0.9rem;
        transition: all 0.3s ease;
    }
    .stButton > button:hover {
        background-color: #e5e7eb;
        border-color: #9ca3af;
    }
    .stButton > button:active {
        background-color: #d1d5db;
    }
    </style>
    """

st.markdown(load_css(), unsafe_allow_html=True)

def generate_summary(input_text, base_prompt, selected_prompt, audio_file_path=None):
    """
    Generate a summary with progress updates.

    :param input_text: The input text to summarize.
    :param base_prompt: The base prompt for summarization.
    :param selected_prompt: The selected prompt for summarization.
    :param audio_file_path: Path to the audio file, if applicable.
    :return: Generated summary.
    """

    try:
        # Check if this is a long recording prompt
        is_long_recording = st.session_state.get('is_long_recording', False)
        
        progress_placeholder = st.empty()
        total_steps = 3  # Example total steps for summarization

        if is_long_recording and audio_file_path:
            update_progress(progress_placeholder, "Starting enhanced summary generation", 1, total_steps)
            summary = generate_enhanced_summary(audio_file_path, client)
            update_progress(progress_placeholder, "Enhanced summary generation complete", 2, total_steps)
        else:
            update_progress(progress_placeholder, "Preparing prompt for summarization", 1, total_steps)
            full_prompt = f"{base_prompt}\n\n{selected_prompt}"
            response = client.chat.completions.create(
                model=SUMMARY_MODEL,
                messages=[
                    {"role": "system", "content": full_prompt},
                    {"role": "user", "content": input_text}
                ],
                max_tokens=MAX_TOKENS,
                temperature=TEMPERATURE,
                top_p=TOP_P,
                frequency_penalty=FREQUENCY_PENALTY,
                presence_penalty=PRESENCE_PENALTY,
                n=1,
                stop=None
            )
            update_progress(progress_placeholder, "Summarization in progress", 2, total_steps)
            summary = response.choices[0].message.content.strip()
            update_progress(progress_placeholder, "Summarization complete", 3, total_steps)
        
        if not summary:
            raise ValueError("Generated summary is empty")
        
        # Example QA loop integration
        update_progress(progress_placeholder, "Starting QA loop", 1, total_steps)
        # Perform QA loop operations here
        update_progress(progress_placeholder, "QA loop complete", 2, total_steps)

        return summary
    except Exception as e:
        print(f"An error occurred while generating the summary: {str(e)}")  # Debug print
        return None

def update_progress(progress_placeholder, step_description, current_step, total_steps):
    """
    Update the progress bar and status message in the Streamlit app.

    :param progress_placeholder: Streamlit placeholder for the progress bar.
    :param step_description: Description of the current step.
    :param current_step: Current step number.
    :param total_steps: Total number of steps.
    """
    progress = current_step / total_steps
    progress_placeholder.progress(progress, text=f"{step_description} ({current_step}/{total_steps})")
    progress_placeholder.markdown(
        f"""
        <div style="text-align: center;">
            <strong>{step_description}</strong><br>
            Step {current_step} of {total_steps}<br>
            <progress value="{current_step}" max="{total_steps}" style="width: 100%;"></progress>
        </div>
        """,
        unsafe_allow_html=True
    )
