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

# In app.py, update the load_css function

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
        background-color: rgba(255, 255, 255, 0.9);
        display: flex;
        justify-content: center;
        align-items: center;
        z-index: 9999;
    }
    .loader-content {
        text-align: center;
    }
    .spinner {
        border: 4px solid #f3f3f3;
        border-top: 4px solid #3498db;
        border-radius: 50%;
        width: 40px;
        height: 40px;
        animation: spin 1s linear infinite;
        margin: 0 auto 20px;
    }
    @keyframes spin {
        0% { transform: rotate(0deg); }
        100% { transform: rotate(360deg); }
    }
    .progress-container {
        width: 300px;
        height: 20px;
        background-color: #f0f0f0;
        border-radius: 10px;
        overflow: hidden;
        margin-bottom: 10px;
    }
    .progress-bar {
        height: 100%;
        background-color: #4CAF50;
        transition: width 0.5s ease-in-out;
    }
    </style>
    """
    
    # Ensure HTML content is rendered correctly
    # Ensure HTML content is rendered correctly
    st.markdown(f"""
    <style>
    {css_content}
    {font_awesome}
    {full_screen_loading_css}
    /* Version control navigation */
    .version-control {{
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 1rem;
        background-color: #f7fafc;
        border-radius: 8px;
        padding: 0.5rem;
    }}

    .version-control button {{
        background-color: #4a5568;
        color: white;
        border: none;
        border-radius: 4px;
        padding: 0.5rem 1rem;
        font-weight: 600;
        transition: all 0.3s ease;
    }}

    .version-control button:hover:not(:disabled) {{
        background-color: #2d3748;
    }}

    .version-control button:disabled {{
        background-color: #cbd5e0;
        cursor: not-allowed;
    }}

    .version-info {{
        font-size: 0.9rem;
        color: #4a5568;
        font-weight: 500;
    }}

    /* Summary editing area */
    .summary-edit-area {{
        background-color: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 8px;
        padding: 1rem;
        margin-bottom: 1rem;
    }}

    .summary-edit-area textarea {{
        width: 100%;
        min-height: 200px;
        border: none;
        resize: vertical;
        font-size: 1rem;
        line-height: 1.5;
        color: #2d3748;
    }}

    .summary-edit-area textarea:focus {{
        outline: none;
        box-shadow: 0 0 0 2px rgba(66, 153, 225, 0.2);
    }}

    /* Save changes button */
    .save-changes-btn {{
        background-color: #48bb78;
        color: white;
        border: none;
        border-radius: 4px;
        padding: 0.5rem 1rem;
        font-weight: 600;
        transition: all 0.3s ease;
        margin-top: 1rem;
    }}

    .save-changes-btn:hover {{
        background-color: #38a169;
    }}

    /* Success message for saved changes */
    .save-success-message {{
        background-color: #c6f6d5;
        color: #2f855a;
        padding: 0.5rem 1rem;
        border-radius: 4px;
        margin-top: 1rem;
        font-weight: 500;
        display: inline-block;
    }}

    /* Existing styles... */

    /* Global Styles */
    body {{
        font-family: 'Inter', sans-serif;
        background-color: #f8fafc;
        color: #1a202c;
    }}

    .stApp {{
        background-color: #f8fafc;
    }}

    /* Header Styles */
    h1, h2, h3, h4, h5, h6 {{
        font-weight: 700;
        color: #2c5282;
    }}

    /* Button Styles */
    .stButton > button {{
        background-color: #4a5568;
        color: white;
        border: none;
        border-radius: 8px;
        padding: 12px 24px;
        font-weight: 600;
        transition: all 0.3s ease;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }}

    .prompt-card, .input-method-card {{
        background-color: #ffffff;
        border: 1px solid #e0e0e0;
        border-radius: 10px;
        padding: 20px;
        text-align: center;
        transition: all 0.3s ease;
        cursor: pointer;
    }}

    .prompt-card:hover, .input-method-card:hover {{
        transform: translateY(-5px);
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    }}

    .prompt-card h3, .input-method-card p {{
        margin: 0;
        color: #333;
    }}

    .input-method-card i {{
        font-size: 24px;
        margin-bottom: 10px;
        color: #4a90e2;
    }}

    .stButton > button:hover {{
        background-color: #2d3748;
        box-shadow: 0 4px 6px rgba(50, 50, 93, 0.11), 0 1px 3px rgba(0, 0, 0, 0.08);
        transform: translateY(-1px);
    }}

    /* Input Styles */
    .stTextInput > div > div > input, .stTextArea > div > div > textarea {{
        border-radius: 8px;
        border: 1px solid #e2e8f0;
        padding: 12px;
        transition: all 0.3s ease;
    }}

    .stTextInput > div > div > input:focus, .stTextArea > div > div > textarea:focus {{
        border-color: #4a5568;
        box-shadow: 0 0 0 2px rgba(74, 85, 104, 0.2);
    }}

    /* Progress Bar Styles */
    .stProgress > div > div > div {{
        background-color: #4a5568;
        height: 8px;
        border-radius: 4px;
    }}

    /* Expander Styles */
    .streamlit-expanderHeader {{
        background-color: #edf2f7;
        border-radius: 8px;
        padding: 12px;
        font-weight: 600;
        color: #2d3748;
    }}

    /* Custom Spinner */
    .custom-spinner {{
        display: inline-block;
        position: relative;
        width: 80px;
        height: 80px;
    }}
    .custom-spinner div {{
        position: absolute;
        top: 33px;
        width: 13px;
        height: 13px;
        border-radius: 50%;
        background: #4a5568;
        animation-timing-function: cubic-bezier(0, 1, 1, 0);
    }}
    .custom-spinner div:nth-child(1) {{
        left: 8px;
        animation: custom-spinner1 0.6s infinite;
    }}
    .custom-spinner div:nth-child(2) {{
        left: 8px;
        animation: custom-spinner2 0.6s infinite;
    }}
    .custom-spinner div:nth-child(3) {{
        left: 32px;
        animation: custom-spinner2 0.6s infinite;
    }}
    .custom-spinner div:nth-child(4) {{
        left: 56px;
        animation: custom-spinner3 0.6s infinite;
    }}
    @keyframes custom-spinner1 {{
        0% {{ transform: scale(0); }}
        100% {{ transform: scale(1); }}
    }}
    @keyframes custom-spinner3 {{
        0% {{ transform: scale(1); }}
        100% {{ transform: scale(0); }}
    }}
    @keyframes custom-spinner2 {{
        0% {{ transform: translate(0, 0); }}
        100% {{ transform: translate(24px, 0); }}
    }}

    /* Hide default Streamlit spinner */
    .stSpinner {{
        visibility: hidden !important;
        height: 0 !important;
        position: absolute !important;
    }}

    /* Hide the text inside the spinner */
    .stSpinner > div > span {{
        display: none !important;
    }}

    /* Progress Checkmarks */
    .progress-checkmarks {{
        background-color: #ffffff;
        border-radius: 12px;
        padding: 24px;
        box-shadow: 0 4px 6px rgba(50, 50, 93, 0.11), 0 1px 3px rgba(0, 0, 0, 0.08);
        margin-bottom: 24px;
    }}

    .progress-checkmarks p {{
        margin: 12px 0;
        font-size: 16px;
        display: flex;
        align-items: center;
        color: #4a5568;
    }}

    .progress-checkmarks p::before {{
        content: '⏳';
        margin-right: 12px;
        font-size: 20px;
    }}

    .progress-checkmarks p.completed::before {{
        content: '✅';
    }}

    /* Card-like containers */
    .info-container {{
        background-color: #ffffff;
        border-radius: 12px;
        padding: 24px;
        margin-bottom: 24px;
        box-shadow: 0 4px 6px rgba(50, 50, 93, 0.11), 0 1px 3px rgba(0, 0, 0, 0.08);
        transition: all 0.3s ease;
    }}

    .info-container:hover {{
        box-shadow: 0 8px 12px rgba(50, 50, 93, 0.15), 0 2px 6px rgba(0, 0, 0, 0.12);
        transform: translateY(-2px);
    }}

    /* Sleek Scrollbar */
    ::-webkit-scrollbar {{
        width: 8px;
    }}

    ::-webkit-scrollbar-track {{
        background: #f1f1f1;
        border-radius: 4px;
    }}

    ::-webkit-scrollbar-thumb {{
        background: #cbd5e0;
        border-radius: 4px;
    }}

    ::-webkit-scrollbar-thumb:hover {{
        background: #a0aec0;
    }}

    /* Responsive Design */
    @media (max-width: 768px) {{
        .stButton > button {{
            width: 100%;
        }}

        .info-container {{
            padding: 20px;
        }}
    }}

    /* Custom styles for select boxes */
    .stSelectbox > div > div {{
        border-radius: 8px;
        border: 1px solid #e2e8f0;
    }}

    .stSelectbox > div > div:hover {{
        border-color: #4a5568;
    }}

    /* Custom styles for radio buttons */
    .stRadio > div {{
        background-color: #ffffff;
        border-radius: 8px;
        padding: 12px;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
    }}

    .stRadio > div > label {{
        font-weight: 500;
        color: #4a5568;
    }}

    /* Custom styles for checkboxes */
    .stCheckbox > label {{
        font-weight: 500;
        color: #4a5568;
    }}

    /* Improve readability of text areas */
    .stTextArea > div > div > textarea {{
        font-size: 16px;
        line-height: 1.6;
    }}

    /* Style for the main title */
    .main-title {{
        font-size: 2.5rem;
        font-weight: 800;
        color: #2c5282;
        text-align: center;
        margin-bottom: 2rem;
        text-transform: uppercase;
        letter-spacing: 1px;
    }}

    /* Style for section titles */
    .section-title {{
        font-size: 1.8rem;
        font-weight: 700;
        color: #2d3748;
        margin-bottom: 1rem;
        border-bottom: 2px solid #4a5568;
        padding-bottom: 0.5rem;
    }}

    /* Style for info text */
    .info-text {{
        font-size: 1rem;
        color: #4a5568;
        line-height: 1.6;
        margin-bottom: 1rem;
    }}

    /* Style for success messages */
    .success-message {{
        background-color: #c6f6d5;
        color: #2f855a;
        padding: 12px;
        border-radius: 8px;
        margin-bottom: 1rem;
        font-weight: 500;
    }}

    /* Style for warning messages */
    .warning-message {{
        background-color: #fefcbf;
        color: #d69e2e;
        padding: 12px;
        border-radius: 8px;
        margin-bottom: 1rem;
        font-weight: 500;
    }}

    /* Sidebar styles */
    .sidebar-title {{
        font-size: 1.5rem;
        font-weight: 700;
        color: #2c5282;
        margin-bottom: 0.5rem;
    }}

    .sidebar-text {{
        font-size: 0.9rem;
        color: #4a5568;
        line-height: 1.4;
    }}

    /* Main content area */
    .main-content {{
        padding: 2rem;
        background-color: #ffffff;
        border-radius: 12px;
        box-shadow: 0 4px 6px rgba(50, 50, 93, 0.11), 0 1px 3px rgba(0, 0, 0, 0.08);
    }}

    /* Navigation progress bar */
    .stProgress > div > div > div {{
        background-color: #4299e1;
    }}

    /* Improve contrast for placeholder text */
    ::placeholder {{
        color: #a0aec0 !important;
        opacity: 1 !important;
    }}

    /* Style for links */
    a {{
        color: #4299e1;
        text-decoration: none;
        transition: color 0.3s ease;
    }}

    a:hover {{
        color: #2b6cb0;
        text-decoration: underline;
    }}

    /* New styles for the redesigned UI */

    /* Card Button Styles */
    .card-button {{
        background-color: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 12px;
        padding: 24px;
        text-align: center;
        transition: all 0.3s ease;
        cursor: pointer;
        height: 100%;
        display: flex;
        flex-direction: column;
        justify-content: center;
        align-items: center;
    }}

    .card-button:hover {{
        transform: translateY(-5px);
        box-shadow: 0 4px 6px rgba(50, 50, 93, 0.11), 0 1px 3px rgba(0, 0, 0, 0.08);
    }}

    .card-button h3 {{
        font-size: 1.5rem;
        font-weight: 600;
        color: #2c5282;
        margin-bottom: 0.5rem;
    }}

    .card-button p {{
        font-size: 1rem;
        color: #4a5568;
    }}

    /* Two-column layout */
    .two-column-layout {{
        display: flex;
        gap: 2rem;
    }}

    .column {{
        flex: 1;
        min-width: 0;
    }}

    /* Chat interface styles */
    .chat-message {{
        padding: 1rem;
        border-radius: 8px;
        margin-bottom: 1rem;
    }}

    .user-message {{
        background-color: #e2e8f0;
        margin-left: 2rem;
    }}

    .assistant-message {{
        background-color: #edf2f7;
        margin-right: 2rem;
    }}

    /* Prompt selection styles */
    .prompt-option {{
        background-color: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 8px;
        padding: 1rem;
        margin-bottom: 1rem;
        cursor: pointer;
        transition: all 0.3s ease;
    }}

    .prompt-option:hover {{
        background-color: #edf2f7;
    }}

    .prompt-option.selected {{
        border-color: #4299e1;
        box-shadow: 0 0 0 2px rgba(66, 153, 225, 0.2);
    }}

    /* Summary styles */
    .summary-container {{
        background-color: #ffffff;
        border-radius: 12px;
        padding: 24px;
        box-shadow: 0 4px 6px rgba(50, 50, 93, 0.11), 0 1px 3px rgba(0, 0, 0, 0.08);
    }}

    .summary-actions {{
        display: flex;
        justify-content: space-between;
        margin-top: 1rem;
    }}

    /* Responsive adjustments */
    @media (max-width: 768px) {{
        .two-column-layout {{
            flex-direction: column;
        }}

        .card-button {{
            margin-bottom: 1rem;
        }}
    }}
    </style>
    """, unsafe_allow_html=True)



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
        "Veldhuis Advies": {
            "Pensioen": ["collectief_pensioen", "deelnemersgesprekken_collectief_pensioen", "onderhoudsgesprekkenwerkgever", "pensioen"],
            "Hypotheek": ["hypotheek", "hypotheek_rapport"],
            "Financiele Planning": ["financieelplanningstraject"],
            "Overig": ["adviesgesprek", "ingesproken_notitie", "notulen_brainstorm", "notulen_vergadering", "onderhoudsadviesgesprek", "telefoongesprek"]
        },
        "Veldhuis Advies Groep": {
            "Bedrijven": ["aov", "risico_analyse"],
            "Particulieren": ["expertise_gesprek", "klantrapport", "klantvraag"],
            "Schade": ["schade_beoordeling", "schademelding"],
            "Overig": ["mutatie"]
        },
        "NLG Arbo": {
            "Casemanager": ["casemanager"],
            "Bedrijfsarts": ["gesprek_bedrijfsarts"],
            "Overig": []
        }
    }

    # Custom CSS for minimalistic design
    st.markdown("""
    <style>
    body {
        background-color: white;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
        color: black;
    }
    .stRadio > div {
        display: flex;
        justify-content: space-between;
        margin-bottom: 15px;
    }
    .stSelectbox > div {
        margin-bottom: 15px;
    }
    .stButton > button {
        background-color: #007BFF;
        color: white;
        border: none;
        border-radius: 5px;
        padding: 8px 20px;
        font-size: 14px;
        cursor: pointer;
        transition: background-color 0.2s ease, transform 0.2s ease;
    }
    .stButton > button:hover {
        background-color: #0056b3;
        transform: translateY(-2px);
    }
    </style>
    """, unsafe_allow_html=True)

    # Radio buttons for category selection
    main_category = st.radio("Kies een hoofd categorie:", list(prompt_categories.keys()))
    sub_category = st.radio("Kies een subcategorie:", list(prompt_categories[main_category].keys()))

    # Dropdown for prompt selection
    selected_prompt = st.selectbox("Kies een specifieke instructie:", prompt_categories[main_category][sub_category])

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
    # Create a full-screen overlay
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
        total_steps = 3
        
        # Update progress: Transcribing
        summary_and_output_module.update_progress(progress_placeholder, "transcript_read", 1, total_steps, start_time)
        time.sleep(2)  # Simulate time taken for transcription
        
        # Update progress: Summarizing
        summary_and_output_module.update_progress(progress_placeholder, "summary_generated", 2, total_steps, start_time)
        new_summary = summary_and_output_module.generate_summary(
            st.session_state.input_text,
            st.session_state.base_prompt,
            get_prompt_content(st.session_state.selected_prompt)
        )
        
        # Update progress: Checking
        summary_and_output_module.update_progress(progress_placeholder, "spelling_checked", 3, total_steps, start_time)
        time.sleep(1)  # Simulate time taken for checking
        
        st.session_state.summary_versions.append(new_summary)
        st.session_state.current_version = len(st.session_state.summary_versions) - 1
        st.session_state.summary = new_summary  # Initialize the summary
        st.session_state.step = 'results'
    else:
        st.error("Geen input tekst gevonden. Controleer of je een bestand hebt geüpload, audio hebt opgenomen, of tekst hebt ingevoerd.")
    
    # Remove the overlay
    overlay_placeholder.empty()
    progress_placeholder.empty()
    
    if st.session_state.step == 'results':
        st.rerun()
         
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
