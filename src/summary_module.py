# src/summary_module.py

import streamlit as st
from openai import OpenAI
from src.config import SUMMARY_MODEL, MAX_TOKENS, TEMPERATURE
from st_copy_to_clipboard import st_copy_to_clipboard
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

def generate_summary(input_text, prompt):
    try:
        response = client.chat.completions.create(
            model=SUMMARY_MODEL,
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": input_text}
            ],
            max_tokens=MAX_TOKENS,
            n=1,
            stop=None,
            temperature=TEMPERATURE,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        st.error(f"Er is een fout opgetreden bij het genereren van de samenvatting: {str(e)}")
        return None

def render_summary_generation():
    st.header("Stap 4: Samenvatting")

    if not st.session_state.input_text:
        st.warning("Er is geen tekst om samen te vatten. Ga terug naar de vorige stappen om tekst in te voeren.")
        return

    if not st.session_state.summary:
        with st.spinner("Samenvatting wordt gegenereerd..."):
            summary = generate_summary(st.session_state.input_text, st.session_state.selected_prompt)
            if summary:
                st.session_state.summary = summary
                st.success("Samenvatting succesvol gegenereerd!")
            else:
                st.error("Samenvatting genereren mislukt. Probeer het opnieuw.")

    if st.session_state.summary:
        st.markdown("### Gegenereerde Samenvatting")
        st.markdown(st.session_state.summary)

        if st_copy_to_clipboard(st.session_state.summary):
            st.success("Samenvatting gekopieerd naar klembord!")

        if st.button("Genereer Nieuwe Samenvatting"):
            st.session_state.summary = None
            st.rerun()

        st.markdown("### Feedback")
        with st.form(key="feedback_form"):
            user_name = st.text_input("Uw naam (verplicht bij feedback):")
            feedback = st.radio("Was deze samenvatting nuttig?", ["Positief", "Negatief"])
            additional_feedback = st.text_area("Laat aanvullende feedback achter:")
            submit_button = st.form_submit_button(label="Verzend feedback")

            if submit_button:
                if not user_name:
                    st.warning("Naam is verplicht bij het geven van feedback.", icon="⚠️")
                else:
                    success = send_feedback_email(
                        transcript=st.session_state.input_text,
                        summary=st.session_state.summary,
                        feedback=feedback,
                        additional_feedback=additional_feedback,
                        user_name=user_name
                    )
                    if success:
                        st.success("Bedankt voor uw feedback!")
                    else:
                        st.error("Er is een fout opgetreden bij het verzenden van de feedback. Probeer het later opnieuw.")

        if st.button("Start Nieuwe Samenvatting"):
            for key in ['input_text', 'selected_prompt', 'summary']:
                if key in st.session_state:
                    del st.session_state[key]
            st.session_state.step = 1
            st.rerun()


def send_feedback_email(transcript, summary, feedback, additional_feedback, user_name):
    sender_email = st.secrets["email"]["username"]
    receiver_email = st.secrets["email"]["receiving_email"]
    password = st.secrets["email"]["password"]
    smtp_server = st.secrets["email"]["smtp_server"]
    smtp_port = st.secrets["email"]["smtp_port"]

    message = MIMEMultipart("alternative")
    message["Subject"] = f"Gesprekssamenvatter Feedback - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    message["From"] = sender_email
    message["To"] = receiver_email

    text = f"""
    Naam: {user_name}
    Feedback: {feedback}
    Aanvullende feedback: {additional_feedback}

    Transcript:
    {transcript}

    Samenvatting:
    {summary}
    """

    html = f"""
    <html>
    <body>
        <h2>Gesprekssamenvatter Feedback</h2>
        <p><strong>Naam:</strong> {user_name}</p>
        <p><strong>Feedback:</strong> {feedback}</p>
        <p><strong>Aanvullende feedback:</strong> {additional_feedback}</p>
        
        <h3>Transcript:</h3>
        <pre>{transcript}</pre>
        
        <h3>Samenvatting:</h3>
        <pre>{summary}</pre>
    </body>
    </html>
    """

    part1 = MIMEText(text, "plain")
    part2 = MIMEText(html, "html")

    message.attach(part1)
    message.attach(part2)

    try:
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(sender_email, password)
            server.sendmail(sender_email, receiver_email, message.as_string())
        return True
    except Exception as e:
        st.error(f"Er is een fout opgetreden bij het verzenden van de e-mail: {str(e)}")
        return False