import streamlit as st
from src import config, prompt_module, input_module, summary_and_output_module, ui_components, history_module
from src.utils import post_process_grammar_check, format_currency, load_prompts, get_prompt_content, transcribe_audio, process_text_file, get_prompt_names
import logging
import os
from openai import OpenAI

logging.getLogger('watchdog').setLevel(logging.ERROR)

def load_css():
    css_path = os.path.join('static', 'styles.css')
    with open(css_path) as f:
        css_content = f.read()
    
    # Add Font Awesome for the arrow icon
    font_awesome = '<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/5.15.3/css/all.min.css">'
    
    return f'<style>{css_content}</style>{font_awesome}'

def main():
    st.set_page_config(page_title="Gesprekssamenvatter AI", layout="wide")

    # Apply custom CSS
    st.markdown(load_css(), unsafe_allow_html=True)
    ui_components.apply_custom_css()

    # Initialize OpenAI client
    client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

    # Initialize session state
    if 'step' not in st.session_state:
        st.session_state.step = 'prompt_selection'
    if 'selected_prompt' not in st.session_state:
        st.session_state.selected_prompt = None
    if 'input_text' not in st.session_state:
        st.session_state.input_text = ""
    if 'summary' not in st.session_state:
        st.session_state.summary = ""

    # Load prompts
    prompts = load_prompts()
    st.session_state.base_prompt = prompts.get('base_prompt.txt', '')

    st.markdown("<h1 class='main-title'>Gesprekssamenvatter AI</h1>", unsafe_allow_html=True)

    if st.session_state.step == 'prompt_selection':
        render_prompt_selection()
    elif st.session_state.step == 'input_selection':
        render_input_selection()
    elif st.session_state.step == 'results':
        render_results()

def render_prompt_selection():
    st.markdown("<h2 class='section-title'>Wat wil je doen?</h2>", unsafe_allow_html=True)
    
    # Define categories and their corresponding prompts
    prompt_categories = {
        "Verzekeringen": ["aov", "expertise_gesprek", "klantrapport", "klantvraag", "mutatie", "risico_analyse", "schade_beoordeling", "schademelding"],
        "Financieel": ["financieelplanningstraject", "hypotheek", "hypotheek_rapport"],
        "Pensioen": ["collectief_pensioen", "deelnemersgesprekken_collectief_pensioen", "onderhoudsgesprekkenwerkgever", "pensioen"],
        "Overig": ["adviesgesprek", "gesprek_bedrijfsarts", "ingesproken_notitie", "notulen_brainstorm", "notulen_vergadering", "onderhoudsadviesgesprek", "telefoongesprek"]
    }
    
    # Radio buttons for category selection
    selected_category = st.radio("Kies een categorie:", list(prompt_categories.keys()))
    
    # Dropdown for prompt selection
    selected_prompt = st.selectbox("Kies een specifieke instructie:", prompt_categories[selected_category])
    
    # Button to proceed
    if st.button("Verder ➔"):
        st.session_state.selected_prompt = selected_prompt
        st.session_state.step = 'input_selection'
        st.rerun()

def render_input_selection():
    st.markdown(f"<h2 class='section-title'>Invoermethode voor: {st.session_state.selected_prompt}</h2>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if ui_components.input_method_card("Opnemen", "microphone"):
            st.session_state.input_method = "record"
            input_module.render_audio_input()
    
    with col2:
        if ui_components.input_method_card("Uploaden", "paperclip"):
            st.session_state.input_method = "upload"
            uploaded_file = st.file_uploader("Upload een audio- of tekstbestand", type=config.ALLOWED_AUDIO_TYPES + config.ALLOWED_TEXT_TYPES)
            
            if uploaded_file is not None:
                st.session_state.uploaded_file = uploaded_file
                st.success(f"Bestand '{uploaded_file.name}' succesvol geüpload.")
                st.write(f"Debug: File uploaded - Name: {uploaded_file.name}, Type: {uploaded_file.type}, Size: {uploaded_file.size} bytes")
                
                # Process the file immediately
                try:
                    if uploaded_file.type.startswith('audio/'):
                        st.session_state.input_text = transcribe_audio(uploaded_file)
                    else:
                        st.session_state.input_text = process_text_file(uploaded_file)
                    st.write(f"Debug: File processed, input text length: {len(st.session_state.input_text)}")
                except Exception as e:
                    st.error(f"Error processing file: {str(e)}")
            else:
                st.write("Debug: No file uploaded yet")
    
    with col3:
        if ui_components.input_method_card("Typen", "pencil"):
            st.session_state.input_method = "type"
            st.session_state.input_text = st.text_area("Voer tekst in:", height=200)

    # Display debug information
    st.write("Debug Information:")
    st.write(f"Input method: {st.session_state.get('input_method', 'Not set')}")
    st.write(f"Uploaded file: {getattr(st.session_state.get('uploaded_file'), 'name', 'No file uploaded')}")
    st.write(f"Input text length: {len(st.session_state.get('input_text', ''))}")
    st.write(f"Selected prompt: {st.session_state.get('selected_prompt', 'Not selected')}")

    # Check if we have input text and a selected prompt before enabling the button
    button_disabled = not (st.session_state.get('input_text') and st.session_state.get('selected_prompt'))
    
    if st.button("GENEREER SAMENVATTING", key="start_process_button", disabled=button_disabled):
        process_input_and_generate_summary()
    
    if button_disabled:
        st.warning("Upload een bestand, neem audio op, of voer tekst in voordat je de samenvatting genereert.")

def process_input_and_generate_summary():
    with st.spinner("Bezig met verwerken..."):
        st.write("Debug: Entering process_input_and_generate_summary")
        st.write(f"Debug: Input method: {st.session_state.get('input_method')}")
        st.write(f"Debug: Uploaded file: {st.session_state.get('uploaded_file')}")
        st.write(f"Debug: Input text length: {len(st.session_state.get('input_text', ''))}")
        st.write(f"Debug: Selected prompt: {st.session_state.get('selected_prompt')}")

        if st.session_state.get('input_text') and st.session_state.get('selected_prompt'):
            st.write("Debug: Generating summary")
            st.session_state.summary = summary_and_output_module.generate_summary(
                st.session_state.input_text,
                st.session_state.base_prompt,
                get_prompt_content(st.session_state.selected_prompt)
            )
            st.write("Debug: Summary generated")
            st.session_state.step = 'results'
            st.experimental_rerun()
        else:
            st.error("Er is geen input tekst of geen prompt geselecteerd. Controleer of je een bestand hebt geüpload of tekst hebt ingevoerd, en of je een prompt hebt gekozen.")

def render_results():
    col1, col2 = st.columns([3, 2])
    
    with col1:
        st.markdown("<h2 class='section-title'>Samenvatting</h2>", unsafe_allow_html=True)
        summary_and_output_module.render_summary()
    
    with col2:
        st.markdown("<h2 class='section-title'>Chat</h2>", unsafe_allow_html=True)
        summary_and_output_module.render_chat_interface()

    with st.expander("Bekijk/Bewerk Transcript"):
        edited_transcript = st.text_area("Transcript:", value=st.session_state.input_text, height=300)
        if edited_transcript != st.session_state.input_text:
            st.session_state.input_text = edited_transcript
            if st.button("Genereer opnieuw"):
                st.session_state.summary = summary_and_output_module.generate_summary(
                    st.session_state.input_text,
                    st.session_state.base_prompt,
                    get_prompt_content(st.session_state.selected_prompt)
                )
                st.rerun()

    if st.button("Terug naar begin", key="back_to_start_button"):
        st.session_state.step = 'prompt_selection'
        st.session_state.selected_prompt = None
        st.session_state.input_text = ""
        st.session_state.summary = ""
        st.rerun()

if __name__ == "__main__":
    main()