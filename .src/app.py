import os
import sys
import json
import streamlit as st
from openai_service import perform_gpt4_operation
from utils.audio_processing import transcribe_audio, process_audio_input
from utils.file_processing import process_uploaded_file
from services.summarization_service import run_summarization
from ui.components import display_transcript, display_summary
from ui.pages import render_feedback_form, render_conversation_history
from utils.text_processing import update_gesprekslog, load_questions
from st_copy_to_clipboard import st_copy_to_clipboard
from docx import Document
from docx.shared import Pt
from docx.enum.style import WD_STYLE_TYPE
from io import BytesIO
import bleach
import base64
import time
import logging

logger = logging.getLogger(__name__)

# Configuration
PROMPTS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'prompts'))
QUESTIONS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'questions'))

DEPARTMENTS = [
    "Bedrijven", "Financieel Advies", "Schadeafdeling", "Algemeen", "Arbo", "Algemene samenvatting",
    "Ondersteuning Bedrijfsarts", "Particulieren", "Onderhoudsadviesgesprek in tabelvorm", "Notulen van een vergadering",
    "Verslag van een telefoongesprek", "Deelnemersgesprekken collectief pensioen", "test-prompt (alleen voor Melle!)"
]

INPUT_METHODS = ["Voer tekst in of plak tekst", "Upload tekst", "Upload audio", "Neem audio op"]

def setup_page_style():
    st.markdown("""
    <style>
    .main {
        background-color: #f0f8ff;
        color: #333;
        font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
    }
    .stButton>button {
        background-color: #4CAF50;
        color: white;
        border: none;
        padding: 12px 28px;
        text-align: center;
        text-decoration: none;
        display: inline-block;
        font-size: 16px;
        margin: 4px 2px;
        cursor: pointer;
        border-radius: 30px;
        transition: all 0.3s ease 0s;
        box-shadow: 0 8px 15px rgba(0, 0, 0, 0.1);
    }
    .stButton>button:hover {
        background-color: #45a049;
        box-shadow: 0 15px 20px rgba(46, 229, 157, 0.4);
        transform: translateY(-7px);
    }
    .summary-box {
        border: none;
        border-radius: 15px;
        padding: 25px;
        margin: 20px 0;
        background-color: #ffffff;
        box-shadow: 0 10px 30px rgba(0, 0, 0, 0.1);
        transition: all 0.3s ease;
    }
    .summary-box:hover {
        box-shadow: 0 15px 40px rgba(0, 0, 0, 0.15);
        transform: translateY(-5px);
    }
    .summary-box h3 {
        color: #2c3e50;
        border-bottom: 2px solid #3498db;
        padding-bottom: 10px;
        margin-bottom: 20px;
        text-align: center;
        font-weight: 600;
    }
    .content {
        white-space: pre-wrap;
        word-wrap: break-word;
        font-size: 16px;
        line-height: 1.8;
        color: #34495e;
    }
    .transcript-box {
        border: none;
        border-radius: 10px;
        padding: 15px;
        margin-bottom: 20px;
        background-color: #f9f9f9;
        box-shadow: 0 5px 15px rgba(0, 0, 0, 0.05);
    }
    .copy-button {
        text-align: center;
        margin-top: 20px;
    }
    .stProgress > div > div > div > div {
        background-color: #3498db;
    }
    .stSelectbox {
        color: #2c3e50;
    }
    .stSelectbox > div > div {
        background-color: #ffffff;
        border-radius: 5px;
    }
    .stRadio > div {
        background-color: #ffffff;
        border-radius: 5px;
        padding: 10px;
        box-shadow: 0 2px 5px rgba(0, 0, 0, 0.05);
    }
    .summary-box table {
        border-collapse: collapse;
        width: 100%;
        margin-bottom: 1em;
    }
    .summary-box th, .summary-box td {
        border: 1px solid #ddd;
        padding: 8px;
        text-align: left;
    }
    .summary-box th {
        background-color: #f2f2f2;
        font-weight: bold;
    }
    .summary-box tr:nth-child(even) {
        background-color: #f9f9f9;
    }
    .summary-box tr:hover {
        background-color: #f5f5f5;
    }
    </style>
    """, unsafe_allow_html=True)

def load_config():
    return {
        "PROMPTS_DIR": PROMPTS_DIR,
        "QUESTIONS_DIR": QUESTIONS_DIR,
        "DEPARTMENTS": DEPARTMENTS,
        "INPUT_METHODS": INPUT_METHODS,
    }

def load_product_descriptions():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    json_path = os.path.join(current_dir, 'product_descriptions.json')
    
    try:
        with open(json_path, 'r', encoding='utf-8') as file:
            return json.load(file)
    except Exception as e:
        st.error(f"Error loading product descriptions: {str(e)}")
        return {}

def initialize_session_state():
    defaults = {
        'summary': "",
        'summary_versions': [],
        'current_version_index': -1,
        'department': DEPARTMENTS[0],
        'input_text': "",
        'transcript': "",
        'gesprekslog': [],
        'product_info': "",
        'selected_products': [],
        'transcription_done': False,
        'summarization_done': False,
        'processing_complete': False
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

def display_product_descriptions(product_descriptions):
    if not product_descriptions:
        st.warning("Geen productbeschrijvingen beschikbaar.")
        return
    
    flattened_descriptions = {}
    for key, value in product_descriptions.items():
        if isinstance(value, dict) and 'title' in value:
            flattened_descriptions[key] = value
        elif isinstance(value, dict):
            for subkey, subvalue in value.items():
                if isinstance(subvalue, dict) and 'title' in subvalue:
                    flattened_descriptions[f"{key} - {subkey}"] = subvalue

    selected_products = st.multiselect(
        "Selecteer producten voor extra informatie:",
        options=list(flattened_descriptions.keys()),
        format_func=lambda x: flattened_descriptions[x]['title']
    )
    
    if st.button("Toevoegen aan samenvatting"):
        if selected_products:
            product_info = "## Extra informatie over de besproken producten\n\n"
            for product in selected_products:
                product_info += f"### {flattened_descriptions[product]['title']}\n"
                product_info += f"{flattened_descriptions[product]['description']}\n\n"
            
            if 'summary' in st.session_state and st.session_state.summary:
                st.session_state.summary += "\n\n" + product_info
            else:
                st.session_state.summary = product_info
            
            st.success("Productinformatie is toegevoegd aan de samenvatting.")
            st.rerun()
        else:
            st.warning("Selecteer eerst producten om toe te voegen.")

def create_safe_docx(content):
    doc = Document()
    style = doc.styles.add_style('CustomStyle', WD_STYLE_TYPE.PARAGRAPH)
    font = style.font
    font.name = 'Calibri'
    font.size = Pt(11)
    
    clean_content = bleach.clean(content, tags=['p', 'b', 'i', 'u', 'h1', 'h2', 'h3', 'br'], strip=True)
    
    paragraphs = clean_content.split('\n')
    for para in paragraphs:
        p = doc.add_paragraph(para, style='CustomStyle')

    bio = BytesIO()
    doc.save(bio)
    return bio.getvalue()

def update_summary(new_summary):
    st.session_state.summary_versions.append(new_summary)
    st.session_state.current_version_index = len(st.session_state.summary_versions) - 1
    st.session_state.summary = new_summary

def display_department_info(department):
    if department == "Deelnemersgesprekken collectief pensioen":
        st.info("Let op: Voor deze afdeling wordt een uitgebreider, rapportstijl verslag gemaakt.")
        

def main():
    logger.debug("Starting main function")
    st.set_page_config(page_title="Gesprekssamenvatter", page_icon="🎙️", layout="wide")
    
    setup_page_style()  # Call this function to set up the CSS
    
    config = load_config()
    initialize_session_state()
    logger.debug(f"Initial session state: {st.session_state}")
    
    st.title("Gesprekssamenvatter versie 0.2.5")
    st.markdown("---")

    col1, col2 = st.columns([1, 3])

    with col1:
        st.markdown("### 📋 Configuratie")
        department = st.selectbox(
            "Kies je afdeling", 
            config["DEPARTMENTS"], 
            key='department_select',
            index=config["DEPARTMENTS"].index(st.session_state.department)
        )
        st.session_state.department = department
        logger.debug(f"Selected department: {department}")
        
        display_department_info(department)

        input_method = st.radio("Invoermethode", config["INPUT_METHODS"], key='input_method_radio')
        logger.debug(f"Selected input method: {input_method}")

        if department in config["DEPARTMENTS"]:
            with st.expander("💡 Vragen om te overwegen"):
                questions = load_questions(f"{department.lower().replace(' ', '_')}.txt")
                for question in questions:
                    st.markdown(f"- {question.strip()}")

    with col2:
        st.markdown("### 📝 Invoer & Samenvatting")
        if input_method in ["Upload audio", "Neem audio op"]:
            logger.debug(f"Processing audio input: {input_method}")
            process_audio_input(input_method)
        elif input_method == "Upload tekst":
            uploaded_file = st.file_uploader("Kies een bestand", type=['txt', 'docx', 'pdf'])
            if uploaded_file:
                logger.debug(f"File uploaded: {uploaded_file.name}")
                st.session_state.transcript = process_uploaded_file(uploaded_file)
                logger.debug(f"Transcript processed from file. Length: {len(st.session_state.transcript)}")
                with st.spinner("Samenvatting maken..."):
                    result = run_summarization(st.session_state.transcript, department)
                if result["error"] is None:
                    update_summary(result["summary"])
                    update_gesprekslog(st.session_state.transcript, result["summary"])
                    st.success("Samenvatting voltooid!")
                    logger.debug("Summary completed successfully")
                else:
                    st.error(f"Er is een fout opgetreden: {result['error']}")
                    logger.error(f"Error in summarization: {result['error']}")
        elif input_method == "Voer tekst in of plak tekst":
            st.session_state.input_text = st.text_area("Voer tekst in:", 
                                                       value=st.session_state.input_text, 
                                                       height=200,
                                                       key='input_text_area')
            if st.button("Samenvatten", key='summarize_button'):
                if st.session_state.input_text:
                    logger.debug(f"Text input received. Length: {len(st.session_state.input_text)}")
                    st.session_state.transcript = st.session_state.input_text
                    with st.spinner("Samenvatting maken..."):
                        result = run_summarization(st.session_state.transcript, st.session_state.department)
                    if result["error"] is None:
                        update_summary(result["summary"])
                        update_gesprekslog(st.session_state.transcript, result["summary"])
                        st.success("Samenvatting voltooid!")
                        logger.debug("Summary completed successfully")
                    else:
                        st.error(f"Er is een fout opgetreden: {result['error']}")
                        logger.error(f"Error in summarization: {result['error']}")
                else:
                    st.warning("Voer alstublieft tekst in om samen te vatten.")
                    logger.warning("Summarization attempted with empty input")

        display_transcript(st.session_state.transcript)
        logger.debug(f"Displayed transcript. Length: {len(st.session_state.transcript)}")

        if st.session_state.summary:
            logger.debug("Displaying summary")
            st.markdown("### 📑 Samenvatting")
            
            summary_html = f"""
            <div style="border: 2px solid #4CAF50; border-radius: 10px; padding: 20px; background-color: #f1f8e9; position: relative; margin-bottom: 20px;">
                <div style="position: absolute; top: -15px; left: 10px; background-color: white; padding: 0 10px; font-weight: bold;">Samenvatting</div>
                <div style="margin-bottom: 40px;">
                    {st.session_state.summary}
                </div>
                <div style="position: absolute; bottom: 10px; right: 10px;">
                    <button onclick="copyToClipboard()" style="background-color: #4CAF50; border: none; color: white; padding: 5px 10px; text-align: center; text-decoration: none; display: inline-block; font-size: 14px; margin: 2px 2px; cursor: pointer; border-radius: 3px;">Kopieer (werkt niet altijd)</button>
                    <a href="data:application/vnd.openxmlformats-officedocument.wordprocessingml.document;base64,{base64.b64encode(create_safe_docx(st.session_state.summary)).decode()}" download="samenvatting.docx" style="background-color: #4CAF50; border: none; color: white; padding: 5px 10px; text-align: center; text-decoration: none; display: inline-block; font-size: 14px; margin: 2px 2px; cursor: pointer; border-radius: 3px;">Download</a>
                </div>
            </div>
            """
            
            st.markdown(summary_html, unsafe_allow_html=True)
            
            # JavaScript for copying to clipboard
            st.markdown("""
            <script>
            function copyToClipboard() {
                const summaryText = document.querySelector('div[style*="border: 2px solid #4CAF50"] > div:nth-child(2)').innerText;
                navigator.clipboard.writeText(summaryText).then(function() {
                    alert('Samenvatting gekopieerd naar klembord!');
                }, function() {
                    alert('Kopiëren naar klembord is mislukt. Probeer het opnieuw.');
                });
            }
            </script>
            """, unsafe_allow_html=True)
            
            # Version control and other summary-related functionality...

    st.markdown("---")
    render_conversation_history()

    # Display current state for debugging
    st.write("Current session state:")
    st.write(f"Transcript length: {len(st.session_state.get('transcript', ''))}")
    st.write(f"Summary length: {len(st.session_state.get('summary', ''))}")
    st.write(f"Transcription done: {st.session_state.get('transcription_done', False)}")
    st.write(f"Summarization done: {st.session_state.get('summarization_done', False)}")
    st.write(f"Processing complete: {st.session_state.get('processing_complete', False)}")

    logger.debug("Exiting main function")
    logger.debug(f"Final session state: {st.session_state}")

if __name__ == "__main__":
    product_descriptions = load_product_descriptions()
    main()