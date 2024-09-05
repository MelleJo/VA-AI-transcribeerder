import streamlit as st
from openai import OpenAI
from src.config import SUMMARY_MODEL, MAX_TOKENS, TEMPERATURE, TOP_P, FREQUENCY_PENALTY, PRESENCE_PENALTY
from src.history_module import add_to_history
from src.utils import load_prompts, get_prompt_content
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

client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

def markdown_to_html(markdown_text):
    return markdown2.markdown(markdown_text)

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
        if not summary:
            raise ValueError("Generated summary is empty")
        return summary
    except Exception as e:
        st.error(f"Er is een fout opgetreden bij het genereren van de samenvatting: {str(e)}")
        return None

def customize_summary(current_summary, customization_request, transcript):
    try:
        response = client.chat.completions.create(
            model=SUMMARY_MODEL,
            messages=[
                {"role": "system", "content": "Je bent een AI-assistent die samenvattingen aanpast op basis van specifieke verzoeken. Behoud de essentie van de oorspronkelijke samenvatting, maar pas deze aan volgens het verzoek van de gebruiker."},
                {"role": "user", "content": f"Oorspronkelijke samenvatting:\n\n{current_summary}\n\nTranscript:\n\n{transcript}\n\nAanpassingsverzoek: {customization_request}\n\nPas de samenvatting aan volgens dit verzoek."}
            ],
            max_tokens=MAX_TOKENS,
            temperature=TEMPERATURE,
            top_p=TOP_P,
            frequency_penalty=FREQUENCY_PENALTY,
            presence_penalty=PRESENCE_PENALTY,
            n=1,
            stop=None
        )
        customized_summary = response.choices[0].message.content.strip()
        if not customized_summary:
            raise ValueError("Aangepaste samenvatting is leeg")
        return customized_summary
    except Exception as e:
        st.error(f"Er is een fout opgetreden bij het aanpassen van de samenvatting: {str(e)}")
        return None

def export_to_docx(summary):
    doc = Document()
    styles = doc.styles

    # Ensure 'Body Text' style exists and is configured
    if 'Body Text' not in styles:
        style = styles.add_style('Body Text', WD_STYLE_TYPE.PARAGRAPH)
    else:
        style = styles['Body Text']
    style.font.size = Pt(11)
    style.font.name = 'Calibri'

    # Create a style for headings
    heading_style = styles.add_style('Custom Heading', WD_STYLE_TYPE.PARAGRAPH)
    heading_style.font.size = Pt(14)
    heading_style.font.bold = True
    heading_style.font.color.rgb = RGBColor(0, 0, 139)  # Dark Blue

    # Convert Markdown to HTML
    html = markdown2.markdown(summary)

    # Split the HTML into paragraphs
    paragraphs = re.split(r'</?p>', html)

    for p in paragraphs:
        if p.strip():
            # Check if it's a heading
            if p.startswith('<h'):
                level = int(p[2])
                text = re.sub(r'</?h\d>', '', p).strip()
                para = doc.add_paragraph(text, style='Custom Heading')
                para.paragraph_format.space_after = Pt(12)
            else:
                # Remove any remaining HTML tags
                text = re.sub(r'<.*?>', '', p).strip()
                para = doc.add_paragraph(text, style='Body Text')
                
                # Apply bold formatting
                for run in para.runs:
                    if '<strong>' in p:
                        run.bold = True

    # Save the document to a bytes buffer
    buffer = io.BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    
    return base64.b64encode(buffer.getvalue()).decode()

def export_to_pdf(summary):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=72, leftMargin=72, topMargin=72, bottomMargin=18)

    # Create custom styles
    styles = getSampleStyleSheet()
    
    # Customize the existing Heading1 style
    styles['Heading1'].fontSize = 14
    styles['Heading1'].leading = 16
    styles['Heading1'].textColor = darkblue
    styles['Heading1'].spaceBefore = 12
    styles['Heading1'].spaceAfter = 6

    # Customize the Normal style for justified text
    styles['Normal'].alignment = TA_JUSTIFY

    # Convert Markdown to HTML
    html = markdown2.markdown(summary)

    # Split the HTML into paragraphs
    paragraphs = re.split(r'</?p>', html)

    story = []
    for p in paragraphs:
        if p.strip():
            # Check if it's a heading
            if p.startswith('<h'):
                level = int(p[2])
                text = re.sub(r'</?h\d>', '', p).strip()
                para = Paragraph(text, styles['Heading1'])
            else:
                # Process bold text
                text = p.replace('<strong>', '<b>').replace('</strong>', '</b>')
                # Remove any remaining HTML tags
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

def render_summary_versions(summaries, button_key_prefix):
    if 'current_version' not in st.session_state:
        st.session_state.current_version = 0

    current_summary = summaries[st.session_state.current_version]
    
    # Convert markdown to HTML
    html_summary = markdown2.markdown(current_summary)
    
    # Generate a unique ID for this summary
    summary_id = f"summary_{uuid.uuid4().hex}"

    with st.container():
        # Header
        st.markdown(f"<h3 style='text-align: center; margin-bottom: 10px;'>Samenvatting (Versie {st.session_state.current_version + 1}/{len(summaries)})</h3>", unsafe_allow_html=True)

        # Summary content
        st.markdown(f"""
        <div id="{summary_id}" class='summary-content' data-html-content="{html_summary.replace('"', '&quot;')}">
            {html_summary}
        </div>
        """, unsafe_allow_html=True)

        # Action buttons
        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown(f"""
            <button onclick="copyFormattedText('{summary_id}')" style="width:100%">
                📋 Kopieer (met opmaak)
            </button>
            """, unsafe_allow_html=True)
        with col2:
            b64_docx = export_to_docx(current_summary)
            st.download_button(
                label="📄 Download Word",
                data=base64.b64decode(b64_docx),
                file_name=f"samenvatting_{button_key_prefix}_{st.session_state.current_version+1}.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                use_container_width=True
            )
        with col3:
            b64_pdf = export_to_pdf(current_summary)
            st.download_button(
                label="📁 Download PDF",
                data=base64.b64decode(b64_pdf),
                file_name=f"samenvatting_{button_key_prefix}_{st.session_state.current_version+1}.pdf",
                mime="application/pdf",
                use_container_width=True
            )

        # Version navigation
        col1, col2, col3 = st.columns([1, 2, 1])
        with col1:
            if st.session_state.current_version > 0:
                if st.button("◀ Vorige", key=f"prev_version_{button_key_prefix}", use_container_width=True):
                    st.session_state.current_version -= 1
                    st.rerun()
            else:
                st.empty()
        with col2:
            st.markdown(f"<p class='version-display'>Versie {st.session_state.current_version + 1} van {len(summaries)}</p>", unsafe_allow_html=True)
        with col3:
            if st.session_state.current_version < len(summaries) - 1:
                if st.button("Volgende ▶", key=f"next_version_{button_key_prefix}", use_container_width=True):
                    st.session_state.current_version += 1
                    st.rerun()
            else:
                st.empty()

    # Customization button
    if st.button("✏️ Pas samenvatting aan", key=f"customize_button_{button_key_prefix}", use_container_width=True):
        st.session_state.show_customization = True

    # Customization section
    if st.session_state.get('show_customization', False):
        st.markdown("### Pas de samenvatting aan")
        customization_request = st.text_area("Voer hier uw aanpassingsverzoek in:", key=f"customization_request_{button_key_prefix}")
        if st.button("Pas samenvatting aan", key=f"apply_customization_button_{button_key_prefix}", use_container_width=True):
            with st.spinner("Samenvatting wordt aangepast..."):
                customized_summary = customize_summary(current_summary, customization_request, st.session_state.input_text)
                if customized_summary:
                    summaries.append(customized_summary)
                    st.session_state.current_version = len(summaries) - 1
                    st.success("Samenvatting succesvol aangepast!")
                    st.session_state.show_customization = False
                    st.rerun()
                else:
                    st.error("Aanpassing van de samenvatting mislukt. Probeer het opnieuw.")

def render_summary_and_output():
    st.header("Stap 4: Samenvatting en Output")
    
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
            st.rerun

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