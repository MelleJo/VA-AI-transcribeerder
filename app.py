import streamlit as st
from src import config, prompt_module, input_module, summary_and_output_module, ui_components, history_module
from src.utils import post_process_grammar_check, format_currency, load_prompts, get_prompt_content, transcribe_audio, process_text_file, get_prompt_names, get_prompt_content
import logging
import time
import os
from openai import OpenAI

logging.getLogger('watchdog').setLevel(logging.ERROR)

# Initialize session state variables at the script level
if 'base_prompt' not in st.session_state:
    prompts = load_prompts()
    st.session_state.base_prompt = prompts.get('base_prompt.txt', '')

if 'step' not in st.session_state:
    st.session_state.step = 'prompt_selection'
if 'selected_prompt' not in st.session_state:
    st.session_state.selected_prompt = None
if 'input_text' not in st.session_state:
    st.session_state.input_text = ""
if 'summary_versions' not in st.session_state:
    st.session_state.summary_versions = []
if 'current_version' not in st.session_state:
    st.session_state.current_version = 0
if 'summary' not in st.session_state:
    st.session_state.summary = ""
if 'summaries' not in st.session_state:
    st.session_state.summaries = []
if 'current_version' not in st.session_state:
    st.session_state.current_version = 0

def load_css():
    css_path = os.path.join('static', 'styles.css')
    with open(css_path) as f:
        css_content = f.read()
    
    # Add Font Awesome for icons
    font_awesome = '<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/5.15.3/css/all.min.css">'
    
    return f'<style>{css_content}</style>{font_awesome}'

def main():
    st.set_page_config(page_title="Gesprekssamenvatter AI", layout="wide")

    # Apply custom CSS
    st.markdown(load_css(), unsafe_allow_html=True)
    ui_components.apply_custom_css()

    # Initialize OpenAI client
    client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

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
    if st.button("Verder ➔", key="proceed_button"):
        st.session_state.selected_prompt = selected_prompt
        st.session_state.step = 'input_selection'
        st.rerun()

def handle_input_complete():
    process_input_and_generate_summary()

def render_input_selection():
    st.markdown(f"<h2 class='section-title'>Invoermethode voor: {st.session_state.selected_prompt}</h2>", unsafe_allow_html=True)
    
    is_recording = input_module.render_input_step(handle_input_complete)
    
    if not is_recording and st.session_state.input_text:
        st.markdown("<div class='info-container'>", unsafe_allow_html=True)
        st.markdown("<h3 class='section-title'>Transcript</h3>", unsafe_allow_html=True)
        st.session_state.input_text = st.text_area(
            "Bewerk indien nodig:",
            value=st.session_state.input_text,
            height=300,
            key="final_transcript"
        )
        st.markdown("</div>", unsafe_allow_html=True)

def display_progress_animation():
    progress_placeholder = st.empty()
    progress_html = """
    <div class="full-screen-loader">
        <div class="lds-ellipsis"><div></div><div></div><div></div><div></div></div>
        <div class="progress-text">Transcription in progress... Please wait.</div>
    </div>
    """
    progress_placeholder.markdown(progress_html, unsafe_allow_html=True)
    return progress_placeholder

def process_input_and_generate_summary():
    # Clear the UI and show only the progress animation
    st.markdown("<style>.main-content, .stButton, .stTextArea, .stFileUploader, .stRadio {display: none;}</style>", unsafe_allow_html=True)  # Hide all input elements
    progress_placeholder = display_progress_animation()
    
    if 'input_text' in st.session_state and st.session_state.input_text:
        # Update progress: Transcribing
        st.session_state.input_text = transcribe_audio(st.session_state.input_text)
        summary_and_output_module.update_progress(progress_placeholder, "transcript_read")
        
        # Update progress: Summarizing
        new_summary = summary_and_output_module.generate_summary(
            st.session_state.input_text,
            st.session_state.base_prompt,
            get_prompt_content(st.session_state.selected_prompt)
        )
        summary_and_output_module.update_progress(progress_placeholder, "summary_generated")
        
        # Update progress: Checking
        time.sleep(1)  # Simulate time taken for checking
        summary_and_output_module.update_progress(progress_placeholder, "spelling_checked")
        
        st.session_state.summary_versions.append(new_summary)
        st.session_state.current_version = len(st.session_state.summary_versions) - 1
        st.session_state.summary = new_summary  # Initialize the summary
        st.session_state.step = 'results'
        st.rerun()
    else:
        st.error("Geen input tekst gevonden. Controleer of je een bestand hebt geüpload, audio hebt opgenomen, of tekst hebt ingevoerd.")
    
    progress_placeholder.empty()
         
def render_results():
    st.markdown("<div class='main-content'>", unsafe_allow_html=True)
    col1, col2 = st.columns([3, 2])
    
    with col1:
        st.markdown("<h2 class='section-title'>Summary</h2>", unsafe_allow_html=True)
        summary_and_output_module.render_summary_versions()
    
    with col2:
        st.markdown("<h2 class='section-title'>Chat</h2>", unsafe_allow_html=True)
        summary_and_output_module.render_chat_interface()

    with st.expander("Bekijk/Bewerk Transcript"):
        edited_transcript = st.text_area("Transcript:", value=st.session_state.input_text, height=300)
        if edited_transcript != st.session_state.input_text:
            st.session_state.input_text = edited_transcript
            if st.button("Genereer opnieuw", key="regenerate_button"):
                new_summary = summary_and_output_module.generate_summary(
                    st.session_state.input_text,
                    st.session_state.base_prompt,
                    get_prompt_content(st.session_state.selected_prompt)
                )
                st.session_state.summary_versions.append(new_summary)
                st.session_state.current_version = len(st.session_state.summary_versions) - 1
                st.session_state.summary = new_summary  # Update the summary
                st.rerun()

    if st.button("Terug naar begin", key="back_to_start_button"):
        st.session_state.step = 'prompt_selection'
        st.session_state.selected_prompt = None
        st.session_state.input_text = ""
        st.session_state.summary_versions = []
        st.session_state.current_version = 0
        st.session_state.summary = ""  # Reset the summary
        st.rerun()
    
    st.markdown("</div>", unsafe_allow_html=True)

def render_summary_with_version_control():
    if st.session_state.summary_versions:
        st.markdown("<div class='version-control'>", unsafe_allow_html=True)
        col1, col2, col3 = st.columns([1, 3, 1])
        
        with col1:
            if st.button("◀ Vorige", disabled=st.session_state.current_version == 0, key="prev_version_button"):
                st.session_state.current_version -= 1
                st.session_state.summary = st.session_state.summary_versions[st.session_state.current_version]  # Update the summary
                st.rerun()
        
        with col2:
            st.markdown(f"<p class='version-info'>Versie {st.session_state.current_version + 1} van {len(st.session_state.summary_versions)}</p>", unsafe_allow_html=True)
        
        with col3:
            if st.button("Volgende ▶", disabled=st.session_state.current_version == len(st.session_state.summary_versions) - 1, key="next_version_button"):
                st.session_state.current_version += 1
                st.session_state.summary = st.session_state.summary_versions[st.session_state.current_version]  # Update the summary
                st.rerun()
        
        st.markdown("</div>", unsafe_allow_html=True)
        
        current_summary = st.session_state.summary_versions[st.session_state.current_version]
        st.markdown("<div class='summary-edit-area'>", unsafe_allow_html=True)
        edited_summary = st.text_area("Samenvatting:", value=current_summary, height=400, key="summary_text_area")
        st.markdown("</div>", unsafe_allow_html=True)
        
        if edited_summary != current_summary:
            if st.button("Wijzigingen opslaan", key="save_changes_button"):
                st.session_state.summary_versions.append(edited_summary)
                st.session_state.current_version = len(st.session_state.summary_versions) - 1
                st.session_state.summary = edited_summary  # Update the summary
                st.markdown("<div class='save-success-message'>Wijzigingen opgeslagen als nieuwe versie.</div>", unsafe_allow_html=True)
                st.rerun()
    else:
        st.warning("Geen samenvatting beschikbaar.")

if __name__ == "__main__":
    main()
