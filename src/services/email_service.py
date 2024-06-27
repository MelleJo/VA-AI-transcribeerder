import streamlit as st
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

def send_feedback_email(transcript, summary, feedback, additional_feedback, user_first_name=""):
    try:
        email_secrets = st.secrets["email"]
        user_email = email_secrets.get("receiving_email")
        if not user_email:
            st.error("Email receiving address is not configured properly.")
            return
        
        msg = MIMEMultipart()
        msg['From'] = email_secrets["username"]
        msg['To'] = user_email
        msg['Subject'] = "New Feedback Submission - Gesprekssamenvatter"
        
        body = f"""
        Transcript: {transcript}
        
        Summary: {summary}
        
        Feedback: {feedback}
        
        User First Name: {user_first_name if user_first_name else "Not provided"}
        
        Additional Feedback: {additional_feedback}
        """
        msg.attach(MIMEText(body, 'plain'))
        
        server = smtplib.SMTP(email_secrets["smtp_server"], int(email_secrets["smtp_port"]))
        server.starttls()
        server.login(email_secrets["username"], email_secrets["password"])
        text = msg.as_string()
        server.sendmail(email_secrets["username"], user_email, text)
        server.quit()
        return True
    except Exception as e:
        st.error(f"An error occurred while sending feedback: {str(e)}")
        return False