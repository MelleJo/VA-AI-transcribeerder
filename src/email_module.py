# email_module.py

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from src.config import EMAIL_SENDER, EMAIL_PASSWORD, EMAIL_SMTP_SERVER, EMAIL_SMTP_PORT, COLLEAGUE_EMAILS


def send_email(sender_email, recipient, subject, body):
    try:
        msg = MIMEMultipart()
        msg['From'] = sender_email
        msg['To'] = recipient
        msg['Subject'] = subject

        msg.attach(MIMEText(body, 'plain'))

        with smtplib.SMTP(EMAIL_SMTP_SERVER, EMAIL_SMTP_PORT) as server:
            server.starttls()
            server.login(sender_email, EMAIL_PASSWORD)  # Make sure to use the correct password for the sender
            server.send_message(msg)
        
        return True
    except Exception as e:
        print(f"An error occurred while sending the email: {str(e)}")
        return False

def get_colleague_emails():
    return COLLEAGUE_EMAILS