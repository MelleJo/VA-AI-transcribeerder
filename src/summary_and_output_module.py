import streamlit as st
from openai import OpenAI
from src.config import SUMMARY_MODEL, MAX_TOKENS, TEMPERATURE, TOP_P, FREQUENCY_PENALTY, PRESENCE_PENALTY
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
from src.ui_components import ui_card, ui_button, ui_download_button, ui_copy_button
import smtplib
from email.mime.text import MIMEText
from st_copy_to_clipboard import st_copy_to_clipboard
from email.mime.multipart import MIMEMultipart
import uuid
import time
import pandas as pd

client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

def update_summary_display(response):
    if response["type"] == "summary":
        st.session_state.summaries.append(response["content"])
        st.session_state.current_version = len(st.session_state.summaries) - 1
    elif response["type"] == "email":
        st.session_state.email_version = response["content"]
    elif response["type"] == "main_points":
        st.session_state.main_points = response["content"]
    st.rerun()

def render_summary():
    if not st.session_state.get('summary'):
        if all(key in st.session_state for key in ['input_text', 'selected_prompt', 'base_prompt']):
            with st.spinner("Samenvatting wordt gegenereerd..."):
                st.session_state.summary = generate_summary(
                    st.session_state.input_text,
                    st.session_state.base_prompt,
                    st.session_state.selected_prompt
                )
        else:
            st.warning("Zorg ervoor dat zowel de invoertekst als de prompt zijn geselecteerd voordat u een samenvatting genereert.")
            return

    if st.session_state.summary:
        st.markdown(st.session_state.summary)
    else:
        st.error("Er is een fout opgetreden bij het genereren van de samenvatting. Probeer het opnieuw.")

def render_chat_interface():
    if 'messages' not in st.session_state:
        st.session_state.messages = []

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    if prompt := st.chat_input("Stel een vraag of vraag om wijzigingen in de samenvatting"):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            response = process_chat_request(prompt)
            if response["type"] == "chat":
                st.markdown(response["content"])
                st.session_state.messages.append({"role": "assistant", "content": response["content"]})
            else:
                confirmation_message = get_confirmation_message(response["type"])
                st.markdown(confirmation_message)
                st.session_state.messages.append({"role": "assistant", "content": confirmation_message})
                update_summary_display(response)

def get_confirmation_message(response_type):
    messages = {
        "summary": "Zeker, ik ga de samenvatting aanpassen. Een momentje...",
        "email": "Zeker, ik zal de samenvatting omzetten in een e-mail. Een momentje...",
        "main_points": "Ik ga de hoofdpunten voor u samenvatten. Een ogenblik geduld...",
    }
    return messages.get(response_type, "Ik verwerk uw verzoek. Een moment alstublieft...")

def process_chat_request(prompt):
    current_summary = st.session_state.summaries[-1]
    transcript = st.session_state.input_text
    base_prompt = st.session_state.base_prompt
    selected_prompt = get_prompt_content(st.session_state.selected_prompt)

    messages = [
        {"role": "system", "content": f"{base_prompt}\n{selected_prompt}"},
        {"role": "user", "content": f"Original summary:\n\n{current_summary}\n\nTranscript:\n\n{transcript}\n\nUser request: {prompt}\n\nProcess this request and determine if it's a request to modify the summary, create an email, extract main points, or any other task that should be displayed in the summary screen. If it's a quick question, answer it directly."}
    ]

    response = client.chat.completions.create(
        model=SUMMARY_MODEL,
        messages=messages,
        max_tokens=MAX_TOKENS,
        temperature=TEMPERATURE,
        top_p=TOP_P,
        frequency_penalty=FREQUENCY_PENALTY,
        presence_penalty=PRESENCE_PENALTY,
    )

    ai_response = response.choices[0].message.content.strip()

    # Determine the type of response
    if "New summary version:" in ai_response:
        new_summary = ai_response.split("New summary version:", 1)[1].strip()
        return {"type": "summary", "content": new_summary}
    elif "Email version:" in ai_response:
        email_content = ai_response.split("Email version:", 1)[1].strip()
        return {"type": "email", "content": email_content}
    elif "Main points:" in ai_response:
        main_points = ai_response.split("Main points:", 1)[1].strip()
        return {"type": "main_points", "content": main_points}
    elif ai_response.startswith("This is a quick answer:"):
        return {"type": "chat", "content": ai_response}
    else:
        return {"type": "summary", "content": ai_response}

def strip_html(html):
    return re.sub('<[^<]+?>', '', html)

def markdown_to_html(markdown_text):
    return markdown2.markdown(markdown_text)

def display_progress_checkmarks():
    progress_placeholder = st.empty()
    checkmarks = {
        "transcript_read": "⏳ Transcript lezen...",
        "summary_generated": "⏳ Samenvatting maken...",
        "spelling_checked": "⏳ Spellingscontrole uitvoeren..."
    }
    
    progress_html = "<div style='text-align: center; padding: 20px; background-color: #f0f2f6; border-radius: 10px;'>"
    progress_html += "<div class='stSpinner'></div>"
    for key, value in checkmarks.items():
        progress_html += f"<p>{value}</p>"
    progress_html += "</div>"
    
    progress_placeholder.markdown(progress_html, unsafe_allow_html=True)
    return progress_placeholder, checkmarks

def update_progress(progress_placeholder, checkmarks, step):
    checkmarks[step] = checkmarks[step].replace("⏳", "✅")
    progress_html = "<div style='text-align: center; padding: 20px; background-color: #f0f2f6; border-radius: 10px;'>"
    progress_html += "<div class='stSpinner'></div>"
    for value in checkmarks.values():
        progress_html += f"<p>{value}</p>"
    progress_html += "</div>"
    progress_placeholder.markdown(progress_html, unsafe_allow_html=True)

def generate_summary(input_text, base_prompt, selected_prompt):
    try:
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
        summary = response.choices[0].message.content.strip()
        
        # Post-processing
        summary = post_process_grammar_check(summary)
        summary = format_currency(summary)
        
        if not summary:
            raise ValueError("Generated summary is empty")
        
        # Initialize summaries list if it doesn't exist
        if 'summaries' not in st.session_state:
            st.session_state.summaries = []
        
        st.session_state.summaries.append(summary)
        st.session_state.current_version = len(st.session_state.summaries) - 1
        
        return summary
    except Exception as e:
        st.error(f"An error occurred while generating the summary: {str(e)}")
        return None

        


def customize_summary(current_summary, customization_request, transcript):
    try:
        messages = [
            {"role": "system", "content": "You are an AI-assistant that customizes summaries based on specific requests. Maintain the essence of the original summary but adjust it according to the user's request."},
            {"role": "user", "content": f"Original summary:\n\n{current_summary}\n\nTranscript:\n\n{transcript}\n\nCustomization request: {customization_request}\n\nAdjust the summary according to this request."}
        ]
        
        stream = client.chat.completions.create(
            model=SUMMARY_MODEL,
            messages=messages,
            max_tokens=MAX_TOKENS,
            temperature=TEMPERATURE,
            top_p=TOP_P,
            frequency_penalty=FREQUENCY_PENALTY,
            presence_penalty=PRESENCE_PENALTY,
            stream=True
        )

        customized_summary = ""
        placeholder = st.empty()

        for chunk in stream:
            if chunk.choices[0].delta.content is not None:
                customized_summary += chunk.choices[0].delta.content
                placeholder.markdown(customized_summary + "▌")
            time.sleep(0.01)

        placeholder.markdown(customized_summary)

        if not customized_summary:
            raise ValueError("Customized summary is empty")

        # Update the main summary state
        st.session_state.summary = customized_summary
        st.session_state.summaries.append(customized_summary)
        st.session_state.current_version = len(st.session_state.summaries) - 1

        return customized_summary
    except Exception as e:
        st.error(f"An error occurred while customizing the summary: {str(e)}")
        return None

def export_to_docx(summary):
    doc = Document()
    styles = doc.styles

    if 'Body Text' not in styles:
        style = styles.add_style('Body Text', WD_STYLE_TYPE.PARAGRAPH)
    else:
        style = styles['Body Text']
    style.font.size = Pt(11)
    style.font.name = 'Calibri'

    heading_style = styles.add_style('Custom Heading', WD_STYLE_TYPE.PARAGRAPH)
    heading_style.font.size = Pt(14)
    heading_style.font.bold = True
    heading_style.font.color.rgb = RGBColor(0, 0, 139)  # Dark Blue

    html = markdown2.markdown(summary)
    paragraphs = re.split(r'</?p>', html)

    for p in paragraphs:
        if p.strip():
            if p.startswith('<h'):
                level = int(p[2])
                text = re.sub(r'</?h\d>', '', p).strip()
                para = doc.add_paragraph(text, style='Custom Heading')
                para.paragraph_format.space_after = Pt(12)
            else:
                text = re.sub(r'<.*?>', '', p).strip()
                para = doc.add_paragraph(text, style='Body Text')
                
                for run in para.runs:
                    if '<strong>' in p:
                        run.bold = True

    buffer = io.BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    
    return base64.b64encode(buffer.getvalue()).decode()

def export_to_pdf(summary):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=72, leftMargin=72, topMargin=72, bottomMargin=18)

    styles = getSampleStyleSheet()
    
    styles['Heading1'].fontSize = 14
    styles['Heading1'].leading = 16
    styles['Heading1'].textColor = darkblue
    styles['Heading1'].spaceBefore = 12
    styles['Heading1'].spaceAfter = 6

    styles['Normal'].alignment = TA_JUSTIFY

    html = markdown2.markdown(summary)
    paragraphs = re.split(r'</?p>', html)

    story = []
    for p in paragraphs:
        if p.strip():
            if p.startswith('<h'):
                level = int(p[2])
                text = re.sub(r'</?h\d>', '', p).strip()
                para = Paragraph(text, styles['Heading1'])
            else:
                text = p.replace('<strong>', '<b>').replace('</strong>', '</b>')
                text = re.sub(r'<(?!/?b).*?>', '', text).strip()
                para = Paragraph(text, styles['Normal'])
            story.append(para)
            story.append(Spacer(1, 6))

    doc.build(story)
    buffer.seek(0)
    
    return base64.b64encode(buffer.getvalue()).decode()

def render_summary_buttons(summary, button_key_prefix):
    ui_copy_button(summary, "Kopieer naar klembord (met opmaak)")
    
    col1, col2 = st.columns(2)
    with col1:
        b64_docx = export_to_docx(summary)
        st.download_button(
            label="Download als Word",
            data=base64.b64decode(b64_docx),
            file_name=f"samenvatting_{button_key_prefix}.docx",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )

    with col2:
        b64_pdf = export_to_pdf(summary)
        st.download_button(
            label="Download als PDF",
            data=base64.b64decode(b64_pdf),
            file_name=f"samenvatting_{button_key_prefix}.pdf",
            mime="application/pdf"
        )

def convert_markdown_tables_to_html(text):
    lines = text.split('\n')
    table_start = -1
    html_tables = []
    
    for i, line in enumerate(lines):
        if line.startswith('|') and '-|-' in line:
            table_start = i - 1
        elif table_start != -1 and (not line.startswith('|') or i == len(lines) - 1):
            table_end = i if not line.startswith('|') else i + 1
            markdown_table = '\n'.join(lines[table_start:table_end])
            df = pd.read_csv(io.StringIO(markdown_table), sep='|', skipinitialspace=True).dropna(axis=1, how='all')
            df.columns = df.columns.str.strip()
            html_table = df.to_html(index=False, escape=False, classes='styled-table')
            html_tables.append((table_start, table_end, html_table))
            table_start = -1

    for start, end, html_table in reversed(html_tables):
        lines[start:end] = [html_table]
    
    return '\n'.join(lines)

def render_summary_versions():
    if 'summaries' not in st.session_state or not st.session_state.summaries:
        st.warning("No summary available yet.")
        return

    current_summary = st.session_state.summaries[st.session_state.current_version]
    st.markdown(current_summary)

    if 'email_version' in st.session_state:
        with st.expander("Email Version"):
            st.markdown(st.session_state.email_version)

    if 'main_points' in st.session_state:
        with st.expander("Main Points"):
            st.markdown(st.session_state.main_points)

    col1, col2, col3 = st.columns([1, 2, 1])
    with col1:
        if st.button("◀ Previous", disabled=st.session_state.current_version == 0):
            st.session_state.current_version -= 1
            st.rerun()
    with col2:
        st.markdown(f"Version {st.session_state.current_version + 1} of {len(st.session_state.summaries)}")
    with col3:
        if st.button("Next ▶", disabled=st.session_state.current_version == len(st.session_state.summaries) - 1):
            st.session_state.current_version += 1
            st.rerun()

def render_summary_and_output():
    prompts = load_prompts()
    base_prompt = prompts.get('base_prompt.txt', '')
    prompt_name = st.session_state.get('selected_prompt', 'None')
    selected_prompt = get_prompt_content(prompt_name)
    
    input_text_length = len(st.session_state.get('input_text', ''))

    with st.expander("Debug Info"):
        st.write(f"Geselecteerde prompt: {prompt_name}")
        st.write(f"Basis prompt geladen: {'Ja' if base_prompt else 'Nee'}")
        st.write(f"Geselecteerde prompt geladen: {'Ja' if selected_prompt else 'Nee'}")
        st.write(f"Lengte invoertekst: {input_text_length} tekens")
        st.write(f"Max tokens voor samenvatting: {MAX_TOKENS}")

    if not st.session_state.input_text:
        st.warning("Er is geen tekst om samen te vatten. Ga terug naar de vorige stappen om tekst in te voeren.")
        return

    summary_placeholder = st.empty()

    if not st.session_state.summary:
        with st.spinner("Samenvatting wordt gegenereerd..."):
            summary = generate_summary(st.session_state.input_text, base_prompt, selected_prompt)
            if summary:
                st.session_state.summary = summary
                st.session_state.summaries = [summary]
                add_to_history(prompt_name, st.session_state.input_text, summary)
                summary_placeholder.success("Samenvatting succesvol gegenereerd! Ik hoor graag feedback (negatief én positief!) via de feedbacktool onderin het scherm.")
            else:
                summary_placeholder.error("Samenvatting genereren mislukt. Probeer het opnieuw.")

    if st.session_state.summary:
        render_summary_versions(st.session_state.summaries, "initial")

        if ui_button("Pas samenvatting aan", lambda: setattr(st.session_state, 'show_customization', True), "customize_summary_button"):
            st.session_state.show_customization = True

        if st.session_state.get('show_customization', False):
            st.markdown("### Pas de samenvatting aan")
            customization_request = st.text_area("Voer hier uw aanpassingsverzoek in (bijv. 'Maak het korter', 'Voeg meer details toe over X', 'Maak het formeler'):", key="customization_request")
            if ui_button("Pas samenvatting aan", lambda: None, "apply_customization_button", primary=True):
                with st.spinner("Samenvatting wordt aangepast..."):
                    customized_summary = customize_summary(st.session_state.summary, customization_request, st.session_state.input_text)
                    if customized_summary:
                        st.session_state.summaries.append(customized_summary)
                        st.session_state.current_version = len(st.session_state.summaries) - 1
                        st.success("Samenvatting succesvol aangepast!")
                        st.rerun()
                    else:
                        st.error("Aanpassing van de samenvatting mislukt. Probeer het opnieuw.")

        if ui_button("Genereer Nieuwe Samenvatting", lambda: setattr(st.session_state, 'summary', None), "generate_new_summary_button"):
            for key in ['summary', 'summaries', 'current_version', 'show_customization']:
                if key in st.session_state:
                    del st.session_state[key]
            st.rerun()

        st.markdown("### Feedback")
        with st.form(key="feedback_form"):
            user_name = st.text_input("Uw naam (verplicht bij feedback):", key="feedback_name")
            feedback = st.radio("Was deze samenvatting nuttig?", ["Positief", "Negatief"], key="feedback_rating")
            additional_feedback = st.text_area("Laat aanvullende feedback achter:", key="additional_feedback")
            submit_button = st.form_submit_button(label="Verzend feedback")

            if submit_button:
                if not user_name:
                    st.warning("Naam is verplicht bij het geven van feedback.", icon="⚠️")
                else:
                    success = send_feedback_email(
                        transcript=st.session_state.input_text,
                        summary=st.session_state.summaries[0],
                        revised_summary=st.session_state.summaries[-1] if len(st.session_state.summaries) > 1 else 'Geen aangepaste samenvatting',
                        feedback=feedback,
                        additional_feedback=additional_feedback,
                        user_name=user_name,
                        selected_prompt=prompt_name
                    )
                    if success:
                        st.success("Bedankt voor uw feedback!")
                    else:
                        st.error("Er is een fout opgetreden bij het verzenden van de feedback. Probeer het later opnieuw.")

        if ui_button("Start Nieuwe Samenvatting", lambda: setattr(st.session_state, 'step', 1), "start_new_summary_button"):
            for key in ['input_text', 'selected_prompt', 'summary', 'summaries', 'current_version', 'show_customization']:
                if key in st.session_state:
                    del st.session_state[key]
            st.session_state.step = 1
            st.rerun()

def send_feedback_email(transcript, summary, revised_summary, feedback, additional_feedback, user_name, selected_prompt):
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
        Geselecteerde prompt: {selected_prompt}

        Transcript:
        {transcript}

        Oorspronkelijke Samenvatting:
        {summary}

        Aangepaste Samenvatting:
        {revised_summary}
        """

        html = f"""
        <html>
        <body>
            <h2>Gesprekssamenvatter Feedback</h2>
            <p><strong>Naam:</strong> {user_name}</p>
            <p><strong>Feedback:</strong> {feedback}</p>
            <p><strong>Aanvullende feedback:</strong> {additional_feedback}</p>
            <p><strong>Geselecteerde prompt:</strong> {selected_prompt}</p>
            
            <h3>Transcript:</h3>
            <pre>{transcript}</pre>
            
            <h3>Oorspronkelijke Samenvatting:</h3>
            <pre>{summary}</pre>

            <h3>Aangepaste Samenvatting:</h3>
            <pre>{revised_summary}</pre>
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