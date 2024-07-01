import os
import sys
import json
import streamlit as st
from openai_service import perform_gpt4_operation
from utils.audio_processing import transcribe_audio, process_audio_input
from utils.file_processing import process_uploaded_file
from services.summarization_service import summarize_text
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
    
    if selected_products != st.session_state.selected_products:
        st.session_state.selected_products = selected_products
        if selected_products:
            st.session_state.product_info = "## Extra informatie over de besproken producten\n\n"
            for product in selected_products:
                st.session_state.product_info += f"### {flattened_descriptions[product]['title']}\n"
                st.session_state.product_info += f"{flattened_descriptions[product]['description']}\n\n"
            st.success("Productinformatie is bijgewerkt.")
        else:
            st.session_state.product_info = ""

def create_safe_docx(content):
    doc = Document()
    style = doc.styles.add_style('CustomStyle', WD_STYLE_TYPE.PARAGRAPH)
    font = style.font
    font.name = 'Calibri'
    font.size = Pt(11)
    
    # Sanitize the content
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
                new_summary = summarize_text(st.session_state.transcript, department)
                update_summary(new_summary)
                update_gesprekslog(st.session_state.transcript, new_summary)

        elif input_method == "Voer tekst in of plak tekst":
            st.session_state.input_text = st.text_area("Voer tekst in:", 
                                                    value=st.session_state.input_text, 
                                                    height=200,
                                                    key='input_text_area')
            if st.button("Samenvatten", key='summarize_button'):
                if st.session_state.input_text:
                    st.session_state.transcript = st.session_state.input_text
                    progress_placeholder = st.empty()
                    
                    # Add progress counters
                    with st.spinner("Samenvatting maken..."):
                        start_time = time.time()
                        new_summary = summarize_text(st.session_state.transcript, st.session_state.department)
                        end_time = time.time()
                        
                        if new_summary:
                            update_summary(new_summary)
                            update_gesprekslog(st.session_state.transcript, new_summary)
                            
                            progress_placeholder.success(f"Samenvatting voltooid in {end_time - start_time:.2f} seconden!")
                            
                            # Display the summary in the nice formatted box
                            st.markdown("### 📑 Samenvatting")
                            st.markdown("""
                            <style>
                            .summary-box {
                                border: 2px solid #4CAF50;
                                border-radius: 10px;
                                padding: 20px;
                                background-color: #f1f8e9;
                                position: relative;
                            }
                            .summary-title {
                                position: absolute;
                                top: -15px;
                                left: 10px;
                                background-color: white;
                                padding: 0 10px;
                                font-weight: bold;
                            }
                            .summary-buttons {
                                position: absolute;
                                bottom: 10px;
                                right: 10px;
                            }
                            </style>
                            """, unsafe_allow_html=True)

                            st.markdown(f"""
                            <div class="summary-box">
                                <div class="summary-title">Samenvatting</div>
                                {new_summary}
                                <div class="summary-buttons">
                                    <button onclick="copyToClipboard()">Kopieer</button>
                                    <a href="data:application/vnd.openxmlformats-officedocument.wordprocessingml.document;base64,{base64.b64encode(create_safe_docx(new_summary)).decode()}" download="samenvatting.docx">
                                        <button>Download</button>
                                    </a>
                                </div>
                            </div>
                            """, unsafe_allow_html=True)

                            # JavaScript for copying to clipboard
                            st.markdown("""
                            <script>
                            function copyToClipboard() {
                                const el = document.createElement('textarea');
                                el.value = document.querySelector('.summary-box').innerText;
                                document.body.appendChild(el);
                                el.select();
                                document.execCommand('copy');
                                document.body.removeChild(el);
                                alert('Samenvatting gekopieerd naar klembord!');
                            }
                            </script>
                            """, unsafe_allow_html=True)
                            
                            render_feedback_form()
                        else:
                            progress_placeholder.error("Er is een fout opgetreden bij het maken van de samenvatting. Probeer het opnieuw.")
                else:
                    st.warning("Voer alstublieft tekst in om samen te vatten.")

        elif input_method in ["Upload audio", "Neem audio op"]:
            process_audio_input(input_method)

        display_transcript(st.session_state.transcript)
        
        if st.session_state.summary:
            st.markdown("### 📑 Samenvatting")
            
            # Maak een box voor de samenvatting
            st.markdown("""
            <style>
            .summary-box {
                border: 2px solid #4CAF50;
                border-radius: 10px;
                padding: 20px;
                background-color: #f1f8e9;
                position: relative;
            }
            .summary-title {
                position: absolute;
                top: -15px;
                left: 10px;
                background-color: white;
                padding: 0 10px;
                font-weight: bold;
            }
            .summary-buttons {
                position: absolute;
                bottom: 10px;
                right: 10px;
            }
            </style>
            """, unsafe_allow_html=True)

            st.markdown(f"""
            <div class="summary-box">
                <div class="summary-title">Samenvatting</div>
                {st.session_state.summary}
                <div class="summary-buttons">
                    <button onclick="copyToClipboard()">Kopieer</button>
                    <a href="data:application/vnd.openxmlformats-officedocument.wordprocessingml.document;base64,{base64.b64encode(create_safe_docx(st.session_state.summary)).decode()}" download="samenvatting.docx">
                        <button>Download</button>
                    </a>
                </div>
            </div>
            """, unsafe_allow_html=True)

            # JavaScript voor kopiëren naar klembord
            st.markdown("""
            <script>
            function copyToClipboard() {
                const el = document.createElement('textarea');
                el.value = document.querySelector('.summary-box').innerText;
                document.body.appendChild(el);
                el.select();
                document.execCommand('copy');
                document.body.removeChild(el);
                alert('Samenvatting gekopieerd naar klembord!');
            }
            </script>
            """, unsafe_allow_html=True)

            # Versie navigatie onder de box
            col1, col2 = st.columns(2)
            with col1:
                if st.button("⬅️ Vorige versie") and st.session_state.current_version_index > 0:
                    st.session_state.current_version_index -= 1
                    st.session_state.summary = st.session_state.summary_versions[st.session_state.current_version_index]
                    st.experimental_rerun()
            with col2:
                if st.button("Volgende versie ➡️") and st.session_state.current_version_index < len(st.session_state.summary_versions) - 1:
                    st.session_state.current_version_index += 1
                    st.session_state.summary = st.session_state.summary_versions[st.session_state.current_version_index]
                    st.experimental_rerun()

            st.markdown("### 🛠️ Vervolgacties")
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                if st.button("🔍 Maak korter"):
                    new_summary = perform_gpt4_operation(st.session_state.summary, "maak de samenvatting korter en bondiger")
                    update_summary(new_summary)
            
            with col2:
                if st.button("📊 Zet om in rapport"):
                    new_summary = perform_gpt4_operation(st.session_state.summary, "zet deze samenvatting om in een formeel rapport voor de klant")
                    update_summary(new_summary)
            
            with col3:
                if st.button("📌 Extraheer actiepunten"):
                    new_summary = perform_gpt4_operation(st.session_state.summary, "extraheer duidelijke actiepunten uit deze samenvatting")
                    update_summary(new_summary)
            
            st.markdown("---")
            
            custom_operation = st.text_input("🔧 Aangepaste bewerking:", key="custom_operation_input", 
                                             placeholder="Bijvoorbeeld: Voeg een conclusie toe")
            if st.button("Uitvoeren"):
                with st.spinner("Bezig met bewerking..."):
                    new_summary = perform_gpt4_operation(st.session_state.summary, custom_operation)
                    update_summary(new_summary)
            
            display_product_descriptions(product_descriptions)

    st.markdown("---")
    render_conversation_history()

if __name__ == "__main__":
    product_descriptions = load_product_descriptions()
    main()