import os
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
from src.ui_components import ui_card, ui_button, ui_download_button, ui_copy_button, full_screen_loader, add_loader_css, estimate_time
import smtplib
from email.mime.text import MIMEText
from st_copy_to_clipboard import st_copy_to_clipboard
from email.mime.multipart import MIMEMultipart
import uuid
import time
import pandas as pd
from app import convert_summaries_to_dict_format
from src.email_module import send_email, get_colleague_emails


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


def estimate_remaining_time(start_time, current_step, total_steps):
    elapsed_time = time.time() - start_time
    estimated_total_time = (elapsed_time / current_step) * total_steps
    remaining_time = max(0, estimated_total_time - elapsed_time)
    return f"Geschatte resterende tijd: {int(remaining_time)} seconden"

def update_summary_display(response):
    if 'summaries' not in st.session_state:
        st.session_state.summaries = []
    
    new_summary = {
        "type": response["type"],
        "content": response["content"]
    }
    
    # Determine if the response should be a new summary version or a chat message
    if response["type"] in ["summary", "email", "actiepunten", "main_points"] or len(response["content"].split()) > 50:
        st.session_state.summaries.append(new_summary)
        st.session_state.current_version = len(st.session_state.summaries) - 1
    else:
        # Short responses will be handled as chat messages
        return "chat"
    
    return "summary"

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
    
    if 'greeting_shown' not in st.session_state:
        st.session_state.greeting_shown = False

    if not st.session_state.greeting_shown:
        greeting = ("Hallo collega! Hoe kan ik je helpen? Je kunt mij vragen stellen over de samenvatting of het "
                    "transcript, of mij verzoeken om wijzigingen te maken in de samenvatting. Ook kan ik de "
                    "samenvatting omzetten in een e-mail of rapport. Laat maar weten wat je nodig hebt!")
        st.session_state.messages.append({"role": "assistant", "content": greeting})
        st.session_state.greeting_shown = True

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    if prompt := st.chat_input("Stel een vraag of vraag om wijzigingen in de samenvatting"):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            response = process_chat_request(prompt)
            handle_chat_response(response)

    # Suggestions
    if st.session_state.summaries:
        st.markdown("### Suggesties:")
        # Define static actions here or import from a common configuration
        static_actions = [
            "Informeer collega",
            "Maak uitgebreider",
            "Maak korter",
            "Stel conceptmail op naar de klant",
            "Stuur samenvatting naar jezelf"
        ]
        suggestions = suggest_actions(st.session_state.summaries[-1]["content"], static_actions)
        
        # Create a 2x2 grid for suggestion buttons
        col1, col2 = st.columns(2)
        for i, action in enumerate(suggestions):
            with col1 if i % 2 == 0 else col2:
                if st.button(action, key=f"suggest_action_{i}", use_container_width=True):
                    st.session_state.messages.append({"role": "user", "content": action})
                    response = process_chat_request(action)
                    handle_chat_response(response)
                    st.rerun()

def handle_chat_response(response):
    if response["type"] == "chat":
        st.markdown(response["content"])
        st.session_state.messages.append({"role": "assistant", "content": response["content"]})
    else:
        confirmation_message = get_confirmation_message(response["type"])
        st.markdown(confirmation_message)
        st.session_state.messages.append({"role": "assistant", "content": confirmation_message})
        update_summary_display(response)
    st.rerun()

def suggest_actions(summary, static_actions):
    prompt = f"""
    Analyseer de volgende samenvatting en stel 4 specifieke, uitvoerbare taken voor die de gebruiker aan de AI-samenvattingsassistent zou kunnen vragen. 
    Maak je keuze afhankelijk van het type samenvatting. Neem de rol aan van een gebruiker van de samenvattingstool en bedenk wat je zou willen doen als je de medewerker was die dit gebruikt.
    Context voor jou: de gebruikers van de tool zijn medewerkers van een verzekerings- en financieel adviesbureau. Je kent dus de context een beetje.
    Zorg ervoor dat ze niet hetzelfde zijn als {static_actions}

    Voorbeelden:
    - "Extraheer actiepunten"
    - "Maak de samenvatting korter"
    - "Maak de samenvatting langer"
    - "Stel een e-mail op voor de klant"
    - "Zet om naar een e-mail voor een collega"

    Samenvatting:
    {summary}

    Geef alleen de 4 suggesties, één per regel, zonder extra tekst of nummering.
    Zorg ervoor dat elke suggestie kort is, idealiter 2-4 woorden. Mocht het echt een super goede suggestie zijn, mag die ook langer zijn.
    """
    
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=100,
        temperature=0.1
    )
    
    suggestions = [suggestion.strip() for suggestion in response.choices[0].message.content.strip().split('\n')]
    return suggestions[:4]  # Ensure we return exactly 4 suggestions

def load_css():
    css_path = os.path.join('static', 'styles.css')
    with open(css_path) as f:
        css_content = f.read()
    
    # Add Font Awesome for icons
    font_awesome = '<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/5.15.3/css/all.min.css">'
    
    # Add full-screen loading CSS
    full_screen_loading_css = """
    <style>
    .fullscreen-loader {
        position: fixed;
        top: 0;
        left: 0;
        width: 100vw;
        height: 100vh;
        background-color: rgba(255, 255, 255, 0.8);
        display: flex;
        justify-content: center;
        align-items: center;
        z-index: 9999;
    }
    </style>
    """
    
    return f'<style>{css_content}</style>{font_awesome}{full_screen_loading_css}'

def get_confirmation_message(response_type):
    messages = {
        "summary": "Ik heb de samenvatting aangepast. U kunt het resultaat bekijken in het samenvattingsgedeelte.",
        "email": "Ik heb een conceptmail opgesteld. U kunt deze bekijken in het samenvattingsgedeelte.",
        "main_points": "Ik heb de hoofdpunten samengevat. U kunt deze bekijken in het samenvattingsgedeelte.",
    }
    return messages.get(response_type, "Ik heb uw verzoek verwerkt. Controleer het samenvattingsgedeelte voor het resultaat.")

def process_chat_request(prompt):
    current_summary = st.session_state.summaries[-1]
    transcript = st.session_state.input_text
    base_prompt = st.session_state.base_prompt
    selected_prompt = get_prompt_content(st.session_state.selected_prompt)

    messages = [
        {"role": "system", "content": f"""
        {base_prompt}
        {selected_prompt}

        Important: Format your responses as follows:
        - For simple chat responses, start with "CHAT:"
        - For summary updates, start with "SUMMARY_UPDATE:"
        - For email drafts, start with "EMAIL_DRAFT:"
        - For main points extraction, start with "MAIN_POINTS:"
        - For action points, start with "ACTIEPUNTEN:"
        
        Use only one of these formats per response. If the user request requires multiple types of responses, prioritize the most relevant one and suggest the user asks for the others separately.
        """},
        {"role": "user", "content": f"Original summary:\n\n{current_summary}\n\nTranscript:\n\n{transcript}\n\nUser request: {prompt}\n\nRespond to this request using the specified format."}
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

    response_types = {
        "CHAT:": "chat",
        "SUMMARY_UPDATE:": "summary",
        "EMAIL_DRAFT:": "email",
        "MAIN_POINTS:": "main_points",
        "ACTIEPUNTEN:": "actiepunten"
    }

    for prefix, resp_type in response_types.items():
        if ai_response.startswith(prefix):
            content = ai_response[len(prefix):].strip()
            return {"type": resp_type, "content": content}

    # If no matching prefix is found, treat it as a chat response
    return {"type": "chat", "content": ai_response}

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
    # Ensure HTML content is rendered correctly
    # Ensure HTML content is rendered correctly
    st.markdown(progress_html, unsafe_allow_html=True)
    return progress_placeholder, checkmarks

def update_progress(progress_placeholder, step, current_step, total_steps, start_time):
    steps = {
        "transcript_read": "Transcript lezen",
        "summary_generated": "Samenvatting maken",
        "spelling_checked": "Spellingscontrole uitvoeren"
    }
    
    elapsed_time = time.time() - start_time
    estimated_total_time = (elapsed_time / current_step) * total_steps
    remaining_time = max(0, estimated_total_time - elapsed_time)
    
    step_text = steps.get(step, "Verwerken...")  # Use a default value if the key is missing
    
    progress_html = f"""
    <div class="progress-container">
        <div class="progress-bar" style="width: {(current_step / total_steps) * 100}%;"></div>
    </div>
    <p>{step_text}...</p>
    <p>Geschatte resterende tijd: {int(remaining_time)} seconden</p>
    """
    
    progress_placeholder.markdown(progress_html, unsafe_allow_html=True)
    
    # Update the progress in the full-screen overlay
    st.markdown(
        f"""
        <script>
            var progressContainer = document.getElementById('progress-container');
            if (progressContainer) {{
                progressContainer.innerHTML = `{progress_html}`;
            }}
        </script>
        """,
        unsafe_allow_html=True
    )

def generate_summary(input_text, base_prompt, selected_prompt):
    try:
        full_prompt = f"{base_prompt}\n\n{selected_prompt}"
        
        status_updates = [
            "Transcript analyseren",
            "Samenvatting genereren",
            "Samenvatting optimaliseren",
            "Nacontrole uitvoeren"
        ]
        
        progress_placeholder = st.empty()
        start_time = time.time()
        file_size = len(input_text.encode('utf-8'))  # Use text length as a proxy for 'file size'
        
        for i, status in enumerate(status_updates):
            progress = (i + 1) * 25
            elapsed_time = time.time() - start_time
            estimated_time = estimate_time(file_size, i + 1, len(status_updates), elapsed_time)
            full_screen_loader(progress, "Samenvatting wordt gemaakt...", status_updates, estimated_time)
            time.sleep(1)  # Simulate processing time
        
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
        
        progress_placeholder.empty()
        
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
    ui_copy_button(summary, "Kopieer")
    
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

    convert_summaries_to_dict_format()

    current_summary = st.session_state.summaries[st.session_state.current_version]

    # Version control
    col1, col2, col3 = st.columns([1, 3, 1])
    with col1:
        if st.button("◀ Vorige", disabled=st.session_state.current_version == 0):
            st.session_state.current_version -= 1
            st.rerun()
    with col2:
        st.markdown(f"<div style='text-align: center;'>Versie {st.session_state.current_version + 1} van {len(st.session_state.summaries)}</div>", unsafe_allow_html=True)
    with col3:
        if st.button("Volgende ▶", disabled=st.session_state.current_version == len(st.session_state.summaries) - 1):
            st.session_state.current_version += 1
            st.rerun()

    st.markdown("### Samenvatting")
    if current_summary["type"] == "email":
        st.markdown("**Email Version**")
    elif current_summary["type"] == "actiepunten":
        st.markdown("**Actiepunten**")
    elif current_summary["type"] == "main_points":
        st.markdown("**Main Points**")
    st.markdown(current_summary["content"])

    # Export options
    with st.expander("Export opties"):
        col1, col2, col3 = st.columns(3)
        with col1:
            b64_docx = export_to_docx(current_summary["content"])
            st.download_button(
                label="Download als Word",
                data=base64.b64decode(b64_docx),
                file_name="samenvatting.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            )
        with col2:
            b64_pdf = export_to_pdf(current_summary["content"])
            st.download_button(
                label="Download als PDF",
                data=base64.b64decode(b64_pdf),
                file_name="samenvatting.pdf",
                mime="application/pdf"
            )
        with col3:
            st_copy_to_clipboard(current_summary["content"], "Kopieer")

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
        render_summary_versions()

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
    
def handle_action(action, summary):
    if action == "Informeer collega":
        return create_email_to_colleague(summary)
    elif action == "Maak uitgebreider":
        return process_chat_request("Maak deze samenvatting uitgebreider met meer details uit het transcript.")
    elif action == "Maak korter":
        return process_chat_request("Maak deze samenvatting korter en beknopter, focus alleen op de meest essentiële informatie.")
    elif action == "Stel conceptmail op naar de klant":
        return create_email_to_client(summary)
    elif action == "Stuur samenvatting naar jezelf":
        return send_summary_to_self(summary)
    elif action == "Extraheer actiepunten":
        return process_chat_request("Extraheer alle actiepunten uit deze samenvatting en presenteer ze in een overzichtelijke lijst.")
    else:
        # For AI-generated suggestions, we can pass them directly to process_chat_request
        return process_chat_request(action)

def convert_markdown_to_plain_text(markdown_text):
    # Remove bold (**) and italic (*) formatting
    plain_text = re.sub(r'\*\*(.*?)\*\*|\*(.*?)\*', r'\1\2', markdown_text)
    
    # Convert bullet points to plain text while preserving indentation
    plain_text = re.sub(r'^(\s*)[-*+]\s', r'\1- ', plain_text, flags=re.MULTILINE)
    
    # Convert numbered lists to plain text while preserving indentation
    plain_text = re.sub(r'^(\s*)\d+\.\s', r'\1', plain_text, flags=re.MULTILINE)
    
    # Remove any remaining special Markdown characters
    plain_text = re.sub(r'[#>`_]', '', plain_text)
    
    # Ensure double line breaks between sections
    plain_text = re.sub(r'\n\n+', '\n\n', plain_text)
    
    return plain_text.strip()


def create_email_to_colleague(summary, transcript):
    st.subheader("E-mail naar collega")
    colleague_emails = get_colleague_emails()
    selected_colleague = st.selectbox("Selecteer een collega:", colleague_emails.keys())
    
    # Generate subject using AI
    subject = generate_email_subject(summary)
    
    # Extract user's name from transcript or prompt user
    user_name = extract_user_name(transcript)
    if not user_name:
        user_name = st.text_input("Vul alstublieft uw naam in:", key="user_name_input")
    
    # Convert Markdown to plain text
    plain_summary = convert_markdown_to_plain_text(summary)
    
    email_body = f"""Beste collega,

Hier is een samenvatting van een recent gesprek:

{plain_summary}

Met vriendelijke groet,
{user_name}

---
Ik heb deze samenvatting gemaakt met de Gesprekssamenvattertool. Wil jij deze tool ook gebruiken? Zie Scienta -> AI -> Gesprekssamenvattertool.
"""
    
    if st.button("Verstuur e-mail naar collega"):
        if send_email(colleague_emails[selected_colleague], subject, email_body):
            st.success("E-mail succesvol verstuurd naar collega!")
            st.session_state.show_informeer_collega = False  # Hide the section after sending
        else:
            st.error("Er is een fout opgetreden bij het versturen van de e-mail.")
    
    if st.button("Annuleer"):
        st.session_state.show_informeer_collega = False
        st.rerun()

    return {"type": "chat", "content": "E-mail naar collega voorbereid."}

def generate_email_subject(summary):
    prompt = f"Genereer een korte, beschrijvende onderwerpregel voor een e-mail op basis van deze samenvatting: {summary[:500]}..."
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=50,
        temperature=0.7
    )
    subject = response.choices[0].message.content.strip()
    return f"Samenvatting door AI over: {subject}"

def extract_user_name(transcript):
    # Simple regex to find a name at the beginning of the transcript
    match = re.search(r'^Mijn naam is (\w+)', transcript, re.IGNORECASE | re.MULTILINE)
    if match:
        return match.group(1)
    return None

def create_email_to_client(summary):
    st.subheader("Conceptmail naar klant")
    email_body = process_chat_request("Stel een conceptmail op naar de klant op basis van deze samenvatting.")["content"]
    
    if st.button("Verstuur conceptmail naar jezelf"):
        if send_email(st.secrets["email"]["username"], "Conceptmail voor klant", email_body):
            st.success("Conceptmail succesvol naar jezelf verstuurd!")
        else:
            st.error("Er is een fout opgetreden bij het versturen van de e-mail.")
    
    return {"type": "chat", "content": "Conceptmail voor klant voorbereid."}

def send_summary_to_self(summary):
    st.subheader("Stuur samenvatting naar jezelf")
    email_body = f"Hier is de samenvatting van het recente gesprek:\n\n{summary}"
    
    if st.button("Verstuur samenvatting naar jezelf"):
        if send_email(st.secrets["email"]["username"], "Samenvatting van recent gesprek", email_body):
            st.success("Samenvatting succesvol naar jezelf verstuurd!")
        else:
            st.error("Er is een fout opgetreden bij het versturen van de e-mail.")
    
    return {"type": "chat", "content": "Samenvatting naar jezelf verstuurd."}