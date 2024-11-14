import os
import streamlit as st
import logging
from openai import OpenAI
from src.config import (
    SUMMARY_MODEL,
    MAX_TOKENS,
    TEMPERATURE,
    TOP_P,
    FREQUENCY_PENALTY,
    PRESENCE_PENALTY,
    get_colleague_emails,
)
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
from src.ui_components import (
    ui_card,
    ui_button,
    ui_download_button,
    ui_copy_button,
    full_screen_loader,
    add_loader_css,
    estimate_time,
)
import smtplib
from email.mime.text import MIMEText
from st_copy_to_clipboard import st_copy_to_clipboard
from email.mime.multipart import MIMEMultipart
import uuid
import time
import pandas as pd
from src.state_utils import convert_summaries_to_dict_format
from src.email_module import send_email
from src.enhanced_summary_module import generate_enhanced_summary
from src.progress_utils import update_progress

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
    Generate a summary with progress updates and a QA loop to enhance detail.

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
        total_steps = 5  # Increased steps due to QA loop

        logger.info(f"Input text: {input_text}")
        logger.info(f"Base prompt: {base_prompt}")
        logger.info(f"Selected prompt: {selected_prompt}")

        if is_long_recording and audio_file_path:
            update_progress(progress_placeholder, "Enhanced summary generation gestart", 1, total_steps)
            summary = generate_enhanced_summary(audio_file_path, client)
            update_progress(progress_placeholder, "Enhanced summary generation voltooid", 2, total_steps)
        else:
            update_progress(progress_placeholder, "Voorbereiden op samenvatting", 1, total_steps)
            full_prompt = f"{base_prompt}\n\n{selected_prompt}"
            input_text = str(input_text)  # Ensure input_text is a string
            try:
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
                update_progress(progress_placeholder, "Samenvatting in uitvoering", 2, total_steps)
                summary = response.choices[0].message.content.strip()
                logger.info(f"Generated summary: {summary}")
            except Exception as e:
                logger.error(f"Error during API call: {str(e)}")
                summary = None

            update_progress(progress_placeholder, "Initiële samenvatting voltooid", 3, total_steps)
        
        if not summary:
            raise ValueError("Generated summary is empty")
        
        # Implement QA loop to enhance the summary
        update_progress(progress_placeholder, "Samenvatting verbeteren voor meer detail", 4, total_steps)
        try:
            refinement_prompt = (
                f"De volgende samenvatting moet worden uitgebreid met meer details en informatie:\n\n"
                f"{summary}\n\n"
                "Geef een meer gedetailleerde versie van deze samenvatting, ga dieper in op de inhoud en haal meer nuances naar boven."
            )
            refinement_response = client.chat.completions.create(
                model=SUMMARY_MODEL,
                messages=[
                    {"role": "user", "content": refinement_prompt}
                ],
                max_tokens=MAX_TOKENS,
                temperature=TEMPERATURE,
                top_p=TOP_P,
                frequency_penalty=FREQUENCY_PENALTY,
                presence_penalty=PRESENCE_PENALTY,
                n=1,
                stop=None
            )
            enhanced_summary = refinement_response.choices[0].message.content.strip()
            logger.info(f"Enhanced summary: {enhanced_summary}")
            summary = enhanced_summary
        except Exception as e:
            logger.error(f"Error during summary enhancement: {str(e)}")
            # Keep the initial summary if refinement fails
        
        update_progress(progress_placeholder, "Samenvatting verbetering voltooid", 5, total_steps)
    
        return summary
    except Exception as e:
        logger.error(f"An error occurred while generating the summary: {str(e)}")
        st.error("Er is een fout opgetreden bij het genereren van de samenvatting.")
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
    progress_placeholder.progress(progress)
    progress_placeholder.markdown(
        f"""
        <div style="text-align: center;">
            <strong>{step_description}</strong><br>
            Stap {current_step} van {total_steps}<br>
            <progress value="{current_step}" max="{total_steps}" style="width: 100%;"></progress>
        </div>
        """,
        unsafe_allow_html=True
    )

def handle_action(action_text, summary_content):
    """
    Process the action requested by the user and generate a response.

    :param action_text: The action text to process.
    :param summary_content: The summary content to use.
    :return: Response text.
    """
    # Process the action based on the action_text
    if action_text.lower() == "verstuur e-mail":
        # Create and send an email to the client
        email_sent = create_email(summary_content, email_type='client')
        if email_sent:
            return "E-mail is succesvol verstuurd naar de klant."
        else:
            return "Er is een fout opgetreden bij het versturen van de e-mail."
    elif action_text.lower() == "exporteer pdf":
        # Generate and offer a PDF download
        pdf_data = generate_pdf(summary_content)
        ui_download_button("Download PDF", pdf_data, "samenvatting.pdf", "application/pdf")
        return "PDF is klaar voor download."
    else:
        return f"Actie '{action_text}' is niet herkend."

def handle_chat_response(response):
    """
    Handle the response from the chatbot or action processing.

    :param response: The response text to handle.
    """
    # Display the response in the app
    st.write(response)

def create_email(summary_content, email_type, input_text=None):
    """
    Create and send an email based on the summary content and email type.

    :param summary_content: The summary content to include.
    :param email_type: Type of email to create ('client', 'colleague', etc.).
    :param input_text: The original input text.
    :return: Boolean indicating success.
    """
    try:
        # Prepare email content
        subject = "Samenvatting van het gesprek"
        if email_type == 'client':
            email_body = f"Beste klant,\n\nHierbij de samenvatting van ons gesprek:\n\n{summary_content}\n\nMet vriendelijke groet,\n[Uw naam]"
            recipient_email = st.session_state.get('client_email')
        elif email_type == 'colleague':
            email_body = f"Beste collega,\n\nHierbij de samenvatting van het gesprek:\n\n{summary_content}\n\nMet vriendelijke groet,\n[Uw naam]"
            recipient_email = st.session_state.get('colleague_email')
        else:
            email_body = summary_content
            recipient_email = st.session_state.get('default_email')

        # Send the email using the send_email function
        email_sent = send_email(recipient_email, subject, email_body)

        return email_sent
    except Exception as e:
        logger.error(f"Error sending email: {str(e)}")
        return False

def render_chat_interface():
    """
    Render the chat interface for user interaction.
    """
    st.header("Chat Interface")
    if 'chat_history' not in st.session_state:
        st.session_state['chat_history'] = []

    for message in st.session_state['chat_history']:
        if message['role'] == 'user':
            st.write(f"**Gebruiker:** {message['content']}")
        else:
            st.write(f"**Assistent:** {message['content']}")

    user_input = st.text_input("Typ je bericht hier...", key='chat_input')
    if st.button("Verstuur"):
        st.session_state['chat_history'].append({'role': 'user', 'content': user_input})
        # Process the user's message and generate a response
        assistant_response = process_user_message(user_input)
        st.session_state['chat_history'].append({'role': 'assistant', 'content': assistant_response})

def process_user_message(user_input):
    """
    Process user's message and generate a response.

    :param user_input: The user's input message.
    :return: Assistant's response message.
    """
    # Use OpenAI to generate a response
    try:
        response = client.chat.completions.create(
            model=SUMMARY_MODEL,
            messages=[
                {"role": "user", "content": user_input}
            ],
            max_tokens=150,
            temperature=TEMPERATURE,
            top_p=TOP_P,
            frequency_penalty=FREQUENCY_PENALTY,
            presence_penalty=PRESENCE_PENALTY,
            n=1,
            stop=None
        )
        assistant_response = response.choices[0].message.content.strip()
        return assistant_response
    except Exception as e:
        logger.error(f"Error in chat response: {str(e)}")
        return "Er is een fout opgetreden bij het genereren van een reactie."

def send_feedback_email(feedback_text):
    """
    Send feedback email with the provided information.

    :param feedback_text: Feedback provided by the user.
    :return: Boolean indicating success.
    """
    try:
        subject = "Gebruikersfeedback"
        email_body = f"Er is nieuwe feedback ontvangen:\n\n{feedback_text}\n\nVerzonden op: {datetime.now()}"
        recipient_email = st.secrets["feedback_email"]

        email_sent = send_email(recipient_email, subject, email_body)
        return email_sent
    except Exception as e:
        logger.error(f"Error sending feedback email: {str(e)}")
        return False

def suggest_actions(summary, static_actions):
    """
    Suggest actions based on the provided summary and static actions.

    :param summary: The summary content to analyze.
    :param static_actions: List of static actions to consider.
    :return: List of suggested actions.
    """
    # Use OpenAI to generate action suggestions based on the summary
    try:
        prompt = (
            f"Based on the following summary, suggest next actions that should be taken:\n\n"
            f"{summary}\n\n"
            "Provide a list of actions."
        )
        response = client.chat.completions.create(
            model=SUMMARY_MODEL,
            messages=[
                {"role": "user", "content": prompt}
            ],
            max_tokens=150,
            temperature=0.5,
            n=1,
            stop=None
        )
        ai_suggestions = response.choices[0].message.content.strip().split('\n')
        return static_actions + [suggestion.strip() for suggestion in ai_suggestions if suggestion.strip()]
    except Exception as e:
        logger.error(f"Error generating action suggestions: {str(e)}")
        return static_actions

def generate_pdf(summary_content):
    """
    Generate a PDF file from the summary content.

    :param summary_content: The text to include in the PDF.
    :return: Byte data of the generated PDF.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name='Justify', alignment=TA_JUSTIFY, fontName="Helvetica"))

    story = []
    lines = summary_content.split('\n')

    for line in lines:
        if line.strip() == '':
            story.append(Spacer(1, 12))
        else:
            paragraph = Paragraph(line.strip(), styles["Justify"])
            story.append(paragraph)
            story.append(Spacer(1, 12))

    doc.build(story)
    pdf_data = buffer.getvalue()
    buffer.close()
    return pdf_data
