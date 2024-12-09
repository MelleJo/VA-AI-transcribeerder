import streamlit as st
import os
import gc
import logging
import time
import psutil
import streamlit_shadcn_ui as ui

# Ensure set_page_config is the first Streamlit command
st.set_page_config(page_title="Gesprekssamenvatter AI - testversie 0.0.4", layout="wide")

# Import local modules using specific imports
from src.memory_tracker import get_memory_tracker
from src.memory_management import MemoryManager
from src.config import (
    SUMMARY_MODEL,
    MAX_TOKENS,
    TEMPERATURE,
    PROMPTS_DIR,
    get_openai_api_key,
    get_email_config,
    get_colleague_emails
)
from src.prompt_module import render_prompt_selection
from src.input_module import render_input_step
from src.ui_components import add_loader_css, apply_custom_css, full_screen_loader
from src.history_module import add_to_history, render_history
from src.summary_and_output_module import (
    generate_summary, 
    update_progress, 
    handle_action, 
    handle_chat_response, 
    create_email, 
    render_chat_interface,
    send_feedback_email,
    suggest_actions
)
from src.utils import post_process_grammar_check, format_currency, load_prompts, get_prompt_names, get_prompt_content
from src.state_utils import convert_summaries_to_dict_format

# Get logger for this module
logger = logging.getLogger(__name__)

# Initialize memory manager
memory_manager = MemoryManager()

def convert_summaries_to_dict_format():
    if 'summaries' in st.session_state:
        for i, summary in enumerate(st.session_state.summaries):
            if isinstance(summary, str):
                st.session_state.summaries[i] = {
                    "type": "samenvatting",
                    "content": summary
                }
    
    for old_key in ['actiepunten_versions', 'main_points_versions']:
        if old_key in st.session_state:
            for item in st.session_state[old_key]:
                st.session_state.summaries.append({
                    "type": "actiepunten" if old_key.startswith("actiepunten") else "hoofdpunten",
                    "content": item
                })
            del st.session_state[old_key]

# Initialize session state variables
if 'base_prompt' not in st.session_state:
    prompts = load_prompts()
    st.session_state.base_prompt = prompts.get('base_prompt.txt', '')

def initialize_session_state():
    """Initialize all session state variables"""
    defaults = {
        'step': 'prompt_selection',
        'selected_prompt': None,
        'input_text': "",
        'summary_versions': [],
        'current_version': 0,
        'summary': "",
        'transcription_complete': False,
        'summaries': [],
        'show_informeer_collega': False,
    }
    
    for key, default_value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = default_value

initialize_session_state()

def monitor_memory():
    """Monitor memory usage and clean up if necessary"""
    try:
        process = psutil.Process()
        memory_info = process.memory_info()
        
        # If using more than 75% of available memory, force cleanup
        if memory_info.rss > (psutil.virtual_memory().total * 0.75):
            gc.collect()
            return False
        return True
    except:
        return True

def load_css():
    try:
        css_file = os.path.join(os.path.dirname(__file__), "static", "styles.css")
        with open(css_file, "r") as f:
            css = f.read()
        
        # Inject custom CSS
        st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)

        # Inject Font Awesome link
        st.markdown("""
            <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/5.15.3/css/all.min.css">
        """, unsafe_allow_html=True)

        # Add full-screen loading CSS
        st.markdown("""
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
        """, unsafe_allow_html=True)
    except Exception as e:
        logger.error(f"Error loading CSS: {e}")

def main():
    memory_tracker = get_memory_tracker()
    
    try:
        load_css()
        add_loader_css()
        apply_custom_css()
        convert_summaries_to_dict_format()

        # Check memory status
        memory_ok, message = memory_tracker.check_memory()
        if not memory_ok:
            st.warning(message)

        if st.session_state.step == 'prompt_selection':
            # Clear session when returning to prompt selection
            memory_tracker.clear_session()
            render_prompt_selection()
        elif st.session_state.step == 'input_selection':
            render_input_selection()
        elif st.session_state.step == 'results':
            render_results()
            
    except Exception as e:
        logger.error(f"Application error: {e}")
        st.error("Er is een onverwachte fout opgetreden. Probeer de pagina te verversen.")
        memory_tracker.cleanup()

def render_input_selection():
    ui.markdown(f"<h2 class='section-title'>{st.session_state.selected_prompt}</h2>", unsafe_allow_html=True)
    
    is_recording = render_input_step(handle_input_complete)
    
    if not is_recording and st.session_state.input_text:
        ui.markdown("<div class='info-container'>", unsafe_allow_html=True)
        ui.markdown("<h3 class='section-title'>Transcript</h3>", unsafe_allow_html=True)
        st.session_state.input_text = ui.textarea(
            "Bewerk indien nodig:",
            value=st.session_state.input_text,
            height=300,
            key=f"transcript_edit_{hash(st.session_state.input_text)}"
        )
        ui.markdown("</div>", unsafe_allow_html=True)

def handle_input_complete():
    process_input_and_generate_summary()

def display_progress_animation():
    progress_placeholder = st.empty()
    progress_html = """
    <div style="text-align: center; padding: 20px;">
        <div class="lds-ellipsis"><div></div><div></div><div></div><div></div></div>
        <style>
        .lds-ellipsis {
            display: inline-block;
            position: relative;
            width: 80px;
            height: 80px;
        }
        .lds-ellipsis div {
            position: absolute;
            top: 33px;
            width: 13px;
            height: 13px;
            border-radius: 50%;
            background: #4CAF50;
            animation-timing-function: cubic-bezier(0, 1, 1, 0);
        }
        .lds-ellipsis div:nth-child(1) {
            left: 8px;
            animation: lds-ellipsis1 0.6s infinite;
        }
        .lds-ellipsis div:nth-child(2) {
            left: 8px;
            animation: lds-ellipsis2 0.6s infinite;
        }
        .lds-ellipsis div:nth-child(3) {
            left: 32px;
            animation: lds-ellipsis2 0.6s infinite;
        }
        .lds-ellipsis div:nth-child(4) {
            left: 56px;
            animation: lds-ellipsis3 0.6s infinite;
        }
        @keyframes lds-ellipsis1 {
            0% { transform: scale(0); }
            100% { transform: scale(1); }
        }
        @keyframes lds-ellipsis3 {
            0% { transform: scale(1); }
            100% { transform: scale(0); }
        }
        @keyframes lds-ellipsis2 {
            0% { transform: translate(0, 0); }
            100% { transform: translate(24px, 0); }
        }
        </style>
    </div>
    """
    progress_placeholder.markdown(progress_html, unsafe_allow_html=True)
    return progress_placeholder

def process_input_and_generate_summary():
    overlay_placeholder = st.empty()
    overlay_placeholder.markdown(
        """
        <div class="fullscreen-loader">
            <div class="loader-content">
                <div class="spinner"></div>
                <div id="progress-container"></div>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )
    
    progress_placeholder = st.empty()
    
    if 'input_text' in st.session_state and st.session_state.input_text:
        start_time = time.time()
        total_steps = 2
        
        # Update progress: Preparing
        update_progress(progress_placeholder, "voorbereiden", 1, total_steps)
        
        # Generate Summary
        update_progress(progress_placeholder, "samenvatting_genereren", 2, total_steps)
        new_summary = generate_summary(
            st.session_state.input_text,
            st.session_state.base_prompt,
            get_prompt_content(st.session_state.selected_prompt)
        )
        
        if new_summary:
            if 'summaries' not in st.session_state:
                st.session_state.summaries = []
            st.session_state.summaries.append({"type": "summary", "content": new_summary})
            st.session_state.current_version = len(st.session_state.summaries) - 1
            st.session_state.summary = new_summary
            st.session_state.step = 'results'
        else:
            st.error("Er is een fout opgetreden bij het genereren van de samenvatting.")
    else:
        st.error("Geen invoertekst gevonden. Controleer of je een bestand hebt geüpload, audio hebt opgenomen, of tekst hebt ingevoerd.")
    
    overlay_placeholder.empty()
    progress_placeholder.empty()
    
    if st.session_state.step == 'results':
        st.rerun()

def render_results():
    ui.markdown("<div class='main-content'>", unsafe_allow_html=True)
    
    col1, col2 = ui.columns([3, 2])
    
    with col1:
        ui.markdown("<h2 class='section-title'>Concept samenvatting</h2>", unsafe_allow_html=True)
        
        if st.session_state.summaries:
            current_summary = st.session_state.summaries[st.session_state.current_version]["content"]
            ui.markdown(current_summary, unsafe_allow_html=True)
        else:
            st.warning("Geen samenvatting beschikbaar.")

    with col2:
        ui.markdown("<h2 class='section-title'>Acties</h2>", unsafe_allow_html=True)
        
        # Static action suggestions
        static_actions = [
            "Informeer collega",
            "Maak uitgebreider",
            "Maak korter",
            "Stel conceptmail op naar de klant",
            "Stuur samenvatting naar jezelf",
            "Vraag X aan klant"
        ]
            
        # AI-generated suggestions
        if st.session_state.summaries:
            ai_suggestions = suggest_actions(st.session_state.summaries[-1]["content"], static_actions)
        else:
            ai_suggestions = []
        
        # Combine static and AI-generated suggestions
        all_actions = static_actions + ai_suggestions
        
        # Create a 3x3 grid for action buttons
        for i in range(0, 9, 3):
            cols = ui.columns(3)
            for j in range(3):
                if i + j < len(all_actions):
                    action = all_actions[i + j]
                    if ui.button(action, key=f"action_{i+j}", use_container_width=True):
                        if action == "Vraag X aan klant":
                            st.session_state.show_email_form = True
                            st.session_state.email_type = 'client_request'
                            st.session_state.client_request = ui.text_input("Wat wilt u aan de klant vragen?")
                        elif action == "Informeer collega":
                            st.session_state.show_email_form = True
                            st.session_state.email_type = 'colleague'
                        elif action == "Stuur samenvatting naar jezelf":
                            st.session_state.show_email_form = True
                            st.session_state.email_type = 'self'
                        elif action == "Stel conceptmail op naar de klant":
                            st.session_state.show_email_form = True
                            st.session_state.email_type = 'client'
                        else:
                            response = handle_action(action, st.session_state.summaries[-1]["content"])
                            handle_chat_response(response)
                        st.rerun()

        # Show email form if button was clicked
        if st.session_state.get('show_email_form', False):
            email_type = st.session_state.get('email_type', 'colleague')
            create_email(
                st.session_state.summaries[-1]["content"],
                st.session_state.input_text,
                email_type
            )

        with ui.expander("Chat", expanded=False):
            render_chat_interface()

    with ui.expander("Bekijk/Bewerk Transcript"):
        edited_transcript = ui.textarea("Transcript:", value=st.session_state.input_text, height=300)
        if edited_transcript != st.session_state.input_text:
            st.session_state.input_text = edited_transcript
            if ui.button("Genereer opnieuw", key="regenerate_button"):
                new_summary = generate_summary(
                    st.session_state.input_text,
                    st.session_state.base_prompt,
                    get_prompt_content(st.session_state.selected_prompt)
                )
                st.session_state.summary_versions.append(new_summary)
                st.session_state.current_version = len(st.session_state.summary_versions) - 1
                st.session_state.summary = new_summary
                st.rerun()

    if ui.button("Terug naar begin", key="back_to_start_button"):
        st.session_state.step = 'prompt_selection'
        st.session_state.selected_prompt = None
        st.session_state.input_text = ""
        st.session_state.summary_versions = []
        st.session_state.current_version = 0
        st.session_state.summary = ""
        st.rerun()
    
    # Add Feedback Mechanism
    with ui.expander("Geef feedback", expanded=False):
        ui.markdown("### Feedback")
        with st.form(key="feedback_form"):
            user_name = ui.text_input("Uw naam (verplicht bij feedback):", key="feedback_name")
            feedback = st.radio("Was deze samenvatting nuttig?", ["Positief", "Negatief"], key="feedback_rating")
            additional_feedback = ui.textarea("Laat aanvullende feedback achter:", key="additional_feedback")
            submit_button = ui.button(label="Verzend feedback")

            if submit_button:
                if not user_name:
                    st.warning("Naam is verplicht bij het geven van feedback.", icon="⚠️")
                else:
                    success = send_feedback_email(
                        transcript=st.session_state.input_text,
                        summary=st.session_state.summaries[0]["content"] if st.session_state.summaries else "",
                        revised_summary=st.session_state.summaries[-1]["content"] if len(st.session_state.summaries) > 1 else 'Geen aangepaste samenvatting',
                        feedback=feedback,
                        additional_feedback=additional_feedback,
                        user_name=user_name,
                        selected_prompt=st.session_state.selected_prompt
                    )
                    if success:
                        st.success("Bedankt voor uw feedback!")
                    else:
                        st.error("Er is een fout opgetreden bij het verzenden van de feedback. Probeer het later opnieuw.")

    ui.markdown("</div>", unsafe_allow_html=True)

    # Add Floating Action Button
    ui.markdown(
        """
        <div id="fab-root"></div>
        <script>
            const fabRoot = document.getElementById('fab-root');
            const fabProps = {
                actions: [
                    { label: 'Kopieer', icon: 'content_copy', onClick: () => navigator.clipboard.writeText(document.querySelector('.stMarkdown').textContent) },
                    { label: 'Download Word', icon: 'description', onClick: () => document.querySelector('button[data-testid="stDownloadButton"]').click() },
                    { label: 'Download PDF', icon: 'picture_as_pdf', onClick: () => document.querySelectorAll('button[data-testid="stDownloadButton"]')[1].click() },
                    { label: 'Nieuwe samenvatting', icon: 'add', onClick: () => document.querySelector('button[data-testid="back_to_start_button"]').click() }
                ]
            };
            ReactDOM.render(React.createElement(FloatingActionButton, fabProps), fabRoot);
        </script>
        """,
        unsafe_allow_html=True
    )

def render_summary_with_version_control():
    if st.session_state.summary_versions:
        ui.markdown("<div class='version-control'>", unsafe_allow_html=True)
        col1, col2, col3 = ui.columns([1, 3, 1])
        
        with col1:
            if ui.button("◀ Vorige", disabled=st.session_state.current_version == 0, key="prev_version_button"):
                st.session_state.current_version -= 1
                st.session_state.summary = st.session_state.summary_versions[st.session_state.current_version]
                st.rerun()
        
        with col2:
            ui.markdown(f"<p class='version-info'>Versie {st.session_state.current_version + 1} van {len(st.session_state.summary_versions)}</p>", unsafe_allow_html=True)
        
        with col3:
            if ui.button("Volgende ▶", disabled=st.session_state.current_version == len(st.session_state.summary_versions) - 1, key="next_version_button"):
                st.session_state.current_version += 1
                st.session_state.summary = st.session_state.summary_versions[st.session_state.current_version]
                st.rerun()
        
        ui.markdown("</div>", unsafe_allow_html=True)
        
        current_summary = st.session_state.summary_versions[st.session_state.current_version]
        ui.markdown("<div class='summary-edit-area'>", unsafe_allow_html=True)
        edited_summary = ui.textarea("Samenvatting:", value=current_summary, height=400, key="summary_text_area")
        ui.markdown("</div>", unsafe_allow_html=True)
        
        if edited_summary != current_summary:
            if ui.button("Wijzigingen opslaan", key="save_changes_button"):
                st.session_state.summary_versions.append(edited_summary)
                st.session_state.current_version = len(st.session_state.summary_versions) - 1
                st.session_state.summary = edited_summary
                ui.markdown("<div class='save-success-message'>Wijzigingen opgeslagen als nieuwe versie.</div>", unsafe_allow_html=True)
                st.rerun()
    else:
        st.warning("Geen samenvatting beschikbaar.")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        st.error("Er is een kritieke fout opgetreden. Ververs de pagina om opnieuw te beginnen.")
