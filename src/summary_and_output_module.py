import streamlit as st
from openai import OpenAI
from src.config import SUMMARY_MODEL, MAX_TOKENS, TEMPERATURE, TOP_P, FREQUENCY_PENALTY, PRESENCE_PENALTY
from src.history_module import add_to_history
from src.utils import post_process_grammar_check, format_currency
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

client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

def generate_summary(input_text, base_prompt, selected_prompt):
    """
    Generate a summary based on the input text and selected prompt.
    
    Args:
        input_text (str): The input text to summarize.
        base_prompt (str): The base prompt for the model.
        selected_prompt (str): The selected specific prompt.
    
    Returns:
        str: The generated summary.
    """
    try:
        with st.spinner("Samenvatting wordt gegenereerd..."):
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
            
            summary = post_process_grammar_check(summary)
            summary = format_currency(summary)
            
            if not summary:
                raise ValueError("Generated summary is empty")
            return summary
    except Exception as e:
        st.error(f"Er is een fout opgetreden bij het genereren van de samenvatting: {str(e)}")
        return None

def customize_summary(current_summary, customization_request, transcript):
    """
    Customize the summary based on user request.
    
    Args:
        current_summary (str): The current summary.
        customization_request (str): The user's customization request.
        transcript (str): The original transcript.
    
    Returns:
        str: The customized summary.
    """
    try:
        with st.spinner("Samenvatting wordt aangepast..."):
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
    """
    Export the summary to a Word document.
    
    Args:
        summary (str): The summary to export.
    
    Returns:
        bytes: The Word document as bytes.
    """
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
    
    return buffer.getvalue()

def export_to_pdf(summary):
    """
    Export the summary to a PDF document.
    
    Args:
        summary (str): The summary to export.
    
    Returns:
        bytes: The PDF document as bytes.
    """
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
    
    return buffer.getvalue()

def render_summary_and_output(summary, input_text, selected_prompt):
    """
    Render the summary and output options.
    
    Args:
        summary (str): The generated summary.
        input_text (str): The original input text.
        selected_prompt (str): The selected prompt.
    
    Returns:
        None
    """
    st.subheader("Gegenereerde Samenvatting")
    st.markdown(summary)

    col1, col2 = st.columns(2)
    with col1:
        if st.button("Download als Word"):
            docx_bytes = export_to_docx(summary)
            st.download_button(
                label="Download Word Document",
                data=docx_bytes,
                file_name="samenvatting.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            )
    
    with col2:
        if st.button("Download als PDF"):
            pdf_bytes = export_to_pdf(summary)
            st.download_button(
                label="Download PDF Document",
                data=pdf_bytes,
                file_name="samenvatting.pdf",
                mime="application/pdf"
            )

    if st.button("Pas samenvatting aan"):
        customization_request = st.text_area("Hoe wil je de samenvatting aanpassen?")
        if st.button("Voer aanpassing uit"):
            customized_summary = customize_summary(summary, customization_request, input_text)
            if customized_summary:
                st.success("Samenvatting is aangepast.")
                render_summary_and_output(customized_summary, input_text, selected_prompt)
            else:
                st.error("Aanpassing van de samenvatting is mislukt. Probeer het opnieuw.")

    if st.button("Sla op in geschiedenis"):
        add_to_history(selected_prompt, input_text, summary)
        st.success("Samenvatting is opgeslagen in de geschiedenis.")

    if st.button("Maak nieuwe samenvatting"):
        st.session_state.step = 1
        st.session_state.input_text = ""
        st.session_state.summary = ""
        st.rerun()