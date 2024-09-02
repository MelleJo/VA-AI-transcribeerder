# src/summary_module.py

import streamlit as st
from openai import OpenAI
from src.config import SUMMARY_MODEL, MAX_TOKENS, TEMPERATURE
from src.history_module import add_to_history
from st_copy_to_clipboard import st_copy_to_clipboard
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from src.history_module import add_to_history
import base64
import io
from docx import Document
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter

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
        summary = response.choices[0].message.content.strip()
        if summary == prompt or not summary:
            raise ValueError("Generated summary is empty or identical to prompt")
        return summary
    except Exception as e:
        st.error(f"Er is een fout opgetreden bij het genereren van de samenvatting: {str(e)}")
        return None

def render_summary_generation():
    st.header("Stap 4: Samenvatting")
    
    st.write(f"Debug: Input text length: {len(st.session_state.get('input_text', ''))}")
    st.write(f"Debug: Selected prompt: {st.session_state.get('selected_prompt', 'None')}")

    if not st.session_state.input_text:
        st.warning("Er is geen tekst om samen te vatten. Ga terug naar de vorige stappen om tekst in te voeren.")
        return

    if not st.session_state.summary:
        with st.spinner("Samenvatting wordt gegenereerd..."):
            summary = generate_summary(st.session_state.input_text, st.session_state.selected_prompt)
            if summary:
                st.session_state.summary = summary
                add_to_history(st.session_state.selected_prompt, st.session_state.input_text, summary)
                st.success("Samenvatting succesvol gegenereerd! Ik hoor graag feedback (negatief én positief!) via de feedbacktool onderin het scherm.")
            else:
                st.error("Samenvatting genereren mislukt. Probeer het opnieuw.")

    if st.session_state.summary:
        st.markdown("### Gegenereerde Samenvatting")
        st.markdown(st.session_state.summary)

        if st_copy_to_clipboard(st.session_state.summary):
            st.success("Samenvatting gekopieerd naar klembord!")

        col1, col2 = st.columns(2)
        with col1:
            b64_docx = export_to_docx(st.session_state.summary)
            href_docx = f'<a href="data:application/vnd.openxmlformats-officedocument.wordprocessingml.document;base64,{b64_docx}" download="samenvatting.docx">Download als Word-document</a>'
            st.markdown(href_docx, unsafe_allow_html=True)

        with col2:
            b64_pdf = export_to_pdf(st.session_state.summary)
            href_pdf = f'<a href="data:application/pdf;base64,{b64_pdf}" download="samenvatting.pdf">Download als PDF</a>'
            st.markdown(href_pdf, unsafe_allow_html=True)

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
                        st.success("Bedankt voor de feedback!")
                    else:
                        st.error("Er is een fout opgetreden bij het verzenden van de feedback. Probeer het later opnieuw.")

        if st.button("Start Nieuwe Samenvatting"):
            for key in ['input_text', 'selected_prompt', 'summary']:
                if key in st.session_state:
                    del st.session_state[key]
            st.session_state.step = 1
            st.rerun()


def send_feedback_email(transcript, summary, feedback, additional_feedback, user_name):
    try:
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

        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(sender_email, password)
            server.sendmail(sender_email, receiver_email, message.as_string())
        return True
    except Exception as e:
        st.error(f"Er is een fout opgetreden bij het verzenden van de e-mail: {str(e)}")
        return False
    
def export_to_docx(summary):
    doc = Document()
    doc.add_heading('Samenvatting', 0)
    doc.add_paragraph(summary)
    
    buffer = io.BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    
    b64 = base64.b64encode(buffer.getvalue()).decode()
    return b64

def export_to_pdf(summary):
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter
    c.drawString(50, height - 50, "Samenvatting")
    text = c.beginText(50, height - 100)
    for line in summary.split('\n'):
        text.textLine(line)
    c.drawText(text)
    c.showPage()
    c.save()
    buffer.seek(0)
    
    b64 = base64.b64encode(buffer.getvalue()).decode()
    return b64