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

# Configuration
PROMPTS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'prompts'))
QUESTIONS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'questions'))

DEPARTMENTS = [
    "Bedrijven", "Financieel Advies", "Schadeafdeling", "Algemeen", "Arbo", "Algemene samenvatting",
    "Ondersteuning Bedrijfsarts", "Onderhoudsadviesgesprek in tabelvorm", "Notulen van een vergadering",
    "Verslag van een telefoongesprek", "Deelnemersgesprekken collectief pensioen", "test-prompt (alleen voor Melle!)"
]

INPUT_METHODS = ["Voer tekst in of plak tekst", "Upload tekst", "Upload audio", "Neem audio op"]

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
        'selected_products': []
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
    st.set_page_config(page_title="Gesprekssamenvatter", page_icon="🎙️", layout="wide")
    
    config = load_config()
    initialize_session_state()
    
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
        
        display_department_info(department)  # Add this line

        input_method = st.radio("Invoermethode", config["INPUT_METHODS"], key='input_method_radio')

        if department in config["DEPARTMENTS"]:
            with st.expander("💡 Vragen om te overwegen"):
                questions = load_questions(f"{department.lower().replace(' ', '_')}.txt")
                for question in questions:
                    st.markdown(f"- {question.strip()}")

    with col2:
        st.markdown("### 📝 Invoer & Samenvatting")
        if input_method == "Upload tekst":
            uploaded_file = st.file_uploader("Kies een bestand", type=['txt', 'docx', 'pdf'])
            if uploaded_file:
                st.session_state.transcript = process_uploaded_file(uploaded_file)
                with st.spinner("Samenvatting maken..."):
                    result = run_summarization(st.session_state.transcript, department)
                if result["error"] is None:
                    update_summary(result["summary"])
                    update_gesprekslog(st.session_state.transcript, result["summary"])
                    st.success("Samenvatting voltooid!")
                else:
                    st.error(f"Er is een fout opgetreden: {result['error']}")

        elif input_method == "Voer tekst in of plak tekst":
            st.session_state.input_text = st.text_area("Voer tekst in:", 
                                                       value=st.session_state.input_text, 
                                                       height=200,
                                                       key='input_text_area')
            if st.button("Samenvatten", key='summarize_button'):
                if st.session_state.input_text:
                    st.session_state.transcript = st.session_state.input_text
                    
                    with st.spinner("Samenvatting maken..."):
                        result = run_summarization(st.session_state.transcript, st.session_state.department)
                    
                    if result["error"] is None:
                        update_summary(result["summary"])
                        update_gesprekslog(st.session_state.transcript, result["summary"])
                        st.success("Samenvatting voltooid!")
                    else:
                        st.error(f"Er is een fout opgetreden: {result['error']}")
                else:
                    st.warning("Voer alstublieft tekst in om samen te vatten.")

        elif input_method in ["Upload audio", "Neem audio op"]:
            process_audio_input(input_method)

        display_transcript(st.session_state.transcript)
        with st.expander("Transcript"):
            st.write(st.session_state.transcript)

        if st.session_state.summary:
            st.markdown("### 📑 Samenvatting")
            
            summary_html = f"""
            <div style="border: 2px solid #4CAF50; border-radius: 10px; padding: 20px; background-color: #f1f8e9; position: relative; margin-bottom: 20px;">
                <div style="position: absolute; top: -15px; left: 10px; background-color: white; padding: 0 10px; font-weight: bold;">Samenvatting</div>
                <div style="margin-bottom: 40px;">
                    {st.session_state.summary}
                </div>
                <div style="position: absolute; bottom: 10px; right: 10px;">
                    <button onclick="copyToClipboard()" style="background-color: #4CAF50; border: none; color: white; padding: 5px 10px; text-align: center; text-decoration: none; display: inline-block; font-size: 14px; margin: 2px 2px; cursor: pointer; border-radius: 3px;">Kopieer</button>
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
            
            # Version control
            if len(st.session_state.summary_versions) > 1:
                version_index = st.selectbox("Selecteer versie:", 
                                             range(len(st.session_state.summary_versions)),
                                             format_func=lambda x: f"Versie {x+1}",
                                             index=st.session_state.current_version_index)
                if version_index != st.session_state.current_version_index:
                    st.session_state.current_version_index = version_index
                    st.session_state.summary = st.session_state.summary_versions[version_index]
                    st.rerun()

            st.markdown("### 🛠️ Vervolgacties")
            
            st.markdown("""
            <style>
            .stButton>button {
                width: 100%;
                height: 60px;
                font-size: 16px;
                margin-bottom: 10px;
            }
            </style>
            """, unsafe_allow_html=True)

            col1, col2, col3 = st.columns(3)
            
            with col1:
                if st.button("🔍 Maak korter", key="make_shorter"):
                    new_summary = perform_gpt4_operation(st.session_state.summary, "maak de samenvatting korter en bondiger")
                    update_summary(new_summary)
            
            with col2:
                if st.button("📊 Zet om in rapport", key="convert_to_report"):
                    new_summary = perform_gpt4_operation(st.session_state.summary, "zet deze samenvatting om in een formeel rapport voor de klant")
                    update_summary(new_summary)
            
            with col3:
                if st.button("📌 Extraheer actiepunten", key="extract_action_points"):
                    new_summary = perform_gpt4_operation(st.session_state.summary, "extraheer duidelijke actiepunten uit deze samenvatting")
                    update_summary(new_summary)
            
            st.markdown("---")
            
            st.markdown("### 🔧 Aangepaste bewerking")
            custom_operation = st.text_input("Voer uw aangepaste bewerking in:", key="custom_operation_input", 
                                             placeholder="Bijvoorbeeld: Voeg een conclusie toe")
            if st.button("Uitvoeren", key="execute_custom"):
                with st.spinner("Bezig met bewerking..."):
                    new_summary = perform_gpt4_operation(st.session_state.summary, custom_operation)
                    update_summary(new_summary)
            
            # Display product information
            if st.session_state.product_info:
                st.markdown("### 📚 Productinformatie")
                st.markdown(st.session_state.product_info)
            
            display_product_descriptions(product_descriptions)

    st.markdown("---")
    render_conversation_history()

if __name__ == "__main__":
    product_descriptions = load_product_descriptions()
    main()