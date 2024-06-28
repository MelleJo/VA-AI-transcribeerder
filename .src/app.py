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
from utils.text_processing import update_gesprekslog, copy_to_clipboard, load_questions

# Streamlit configuratie
st.set_page_config(page_title="Gesprekssamenvatter", page_icon="🎙️", layout="wide")

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

def initialize_session_state():
    if 'summary' not in st.session_state:
        st.session_state.summary = ""
    if 'modified_summary' not in st.session_state:
        st.session_state.modified_summary = ""
    if 'show_custom_operation' not in st.session_state:
        st.session_state.show_custom_operation = False
    if 'department' not in st.session_state:
        st.session_state.department = DEPARTMENTS[0]
    if 'input_text' not in st.session_state:
        st.session_state.input_text = ""
    if 'transcript' not in st.session_state:
        st.session_state.transcript = ""
    if 'gesprekslog' not in st.session_state:
        st.session_state.gesprekslog = []

def load_product_descriptions():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    json_path = os.path.join(current_dir, 'product_descriptions.json')
    
    try:
        with open(json_path, 'r', encoding='utf-8') as file:
            content = file.read()
            # Debug: Toon de eerste 500 karakters van de inhoud
            st.text(f"Eerste 500 karakters van JSON inhoud:\n{content[:500]}")
            return json.loads(content)
    except FileNotFoundError:
        st.warning(f"Bestand 'product_descriptions.json' niet gevonden op locatie: {json_path}")
    except json.JSONDecodeError as e:
        st.error(f"Fout bij het decoderen van 'product_descriptions.json': {str(e)}")
        st.text(f"Probleem op positie: {e.pos}")
    except Exception as e:
        st.error(f"Onverwachte fout bij het laden van 'product_descriptions.json': {str(e)}")
    
    return {}  # Return een leeg dictionary als fallback

product_descriptions = load_product_descriptions()

def display_product_descriptions():
    st.subheader("Productbeschrijvingen toevoegen")
    selected_products = st.multiselect(
        "Selecteer producten om toe te voegen aan de samenvatting:",
        options=list(product_descriptions.keys()),
        format_func=lambda x: product_descriptions[x]['title']
    )
    
    if selected_products:
        product_info = "## Productinformatie\n\n"
        for product in selected_products:
            product_info += f"### {product_descriptions[product]['title']}\n"
            product_info += f"{product_descriptions[product]['description']}\n\n"
        
        if 'modified_summary' in st.session_state and st.session_state.modified_summary:
            st.session_state.modified_summary += "\n\n" + product_info
        else:
            st.session_state.modified_summary = st.session_state.summary + "\n\n" + product_info
        st.success("Productbeschrijvingen toegevoegd aan de samenvatting.")

def main():
    config = load_config()
    initialize_session_state()
    
    st.title("Gesprekssamenvatter - 0.2.1")

    col1, col2 = st.columns([1, 3])

    with col1:
        department = st.selectbox(
            "Kies je afdeling", 
            config["DEPARTMENTS"], 
            key='department_select',
            index=config["DEPARTMENTS"].index(st.session_state.department)
        )
        st.session_state.department = department

        input_method = st.radio("Wat wil je laten samenvatten?", config["INPUT_METHODS"], key='input_method_radio')

        if department in config["DEPARTMENTS"]:
            with st.expander("Vragen om te overwegen"):
                questions = load_questions(f"{department.lower().replace(' ', '_')}.txt")
                for question in questions:
                    st.markdown(f"- {question.strip()}")

    with col2:
        if input_method == "Upload tekst":
            uploaded_file = st.file_uploader("Choose a file", type=['txt', 'docx', 'pdf'])
            if uploaded_file:
                st.session_state.transcript = process_uploaded_file(uploaded_file)
                st.session_state.summary = summarize_text(st.session_state.transcript, department)
                update_gesprekslog(st.session_state.transcript, st.session_state.summary)

        elif input_method == "Voer tekst in of plak tekst":
            st.session_state.input_text = st.text_area("Voeg tekst hier in:", 
                                                       value=st.session_state.input_text, 
                                                       height=300,
                                                       key='input_text_area')
            if st.button("Samenvatten", key='summarize_button'):
                if st.session_state.input_text:
                    st.session_state.transcript = st.session_state.input_text
                    st.session_state.summary = summarize_text(st.session_state.transcript, department)
                    update_gesprekslog(st.session_state.transcript, st.session_state.summary)
                else:
                    st.warning("Voer alstublieft wat tekst in om te samenvatten.")

        elif input_method in ["Upload audio", "Neem audio op"]:
            process_audio_input(input_method)

        display_transcript(st.session_state.transcript)
        display_summary(st.session_state.summary)

        if st.session_state.summary:
            st.subheader("Vervolgacties")
            
            col1, col2 = st.columns(2)
            
            with col1:
                if st.button("Maak korter"):
                    st.session_state.modified_summary = perform_gpt4_operation(st.session_state.summary, "maak de samenvatting korter en bondiger")
            
            with col2:
                if st.button("Zet om in rapport"):
                    st.session_state.modified_summary = perform_gpt4_operation(st.session_state.summary, "zet deze samenvatting om in een formeel rapport voor de klant")
            
            if st.button("Extraheer actiepunten"):
                st.session_state.modified_summary = perform_gpt4_operation(st.session_state.summary, "extraheer duidelijke actiepunten uit deze samenvatting")
            
            custom_operation = st.text_input("Typ je gewenste bewerking:", key="custom_operation_input", placeholder="Bijvoorbeeld: Voeg een conclusie toe")
            if st.button("Voer aangepaste bewerking uit"):
                with st.spinner("Bezig met bewerking..."):
                    st.session_state.modified_summary = perform_gpt4_operation(st.session_state.summary, custom_operation)
            
            display_product_descriptions()
            
            if st.session_state.modified_summary:
                st.markdown('<div class="modified-summary-box">', unsafe_allow_html=True)
                st.markdown('<h3>Bewerkte Samenvatting</h3>', unsafe_allow_html=True)
                st.markdown(st.session_state.modified_summary, unsafe_allow_html=True)
                st.markdown('</div>', unsafe_allow_html=True)

            if st.button("Kopieer naar klembord", key='copy_clipboard_button'):
                copy_to_clipboard(st.session_state.transcript, st.session_state.modified_summary or st.session_state.summary)
            
            render_feedback_form()

    render_conversation_history()

if __name__ == "__main__":
    main()