# email_module.py
import streamlit as st
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from src.config import COLLEAGUE_EMAILS

def send_email(sender_email, recipient, subject, body):
    try:
        msg = MIMEMultipart()
        msg['From'] = sender_email
        msg['To'] = recipient
        msg['Subject'] = subject

        msg.attach(MIMEText(body, 'plain'))

        # Get SMTP settings from st.secrets
        smtp_server = st.secrets["email"]["smtp_server"]
        smtp_port = st.secrets["email"]["smtp_port"]
        smtp_username = st.secrets["email"]["username"]
        smtp_password = st.secrets["email"]["password"]

        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(smtp_username, smtp_password)
            server.send_message(msg)
        
        return True, "E-mail succesvol verstuurd"
    except smtplib.SMTPAuthenticationError:
        return False, "Authenticatie mislukt. Controleer de SMTP-inloggegevens."
    except smtplib.SMTPException as e:
        return False, f"SMTP-fout: {str(e)}"
    except Exception as e:
        return False, f"Onverwachte fout: {str(e)}"

def get_colleague_emails():
    return COLLEAGUE_EMAILS