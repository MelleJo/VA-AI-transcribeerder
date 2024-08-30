import streamlit as st

def setup_page_style():
    # Add custom CSS for better styling
    st.markdown("""
        <style>
        .stApp {
            max-width: 1200px;
            margin: 0 auto;
        }
        .stButton > button {
            width: 100%;
        }
        </style>
    """, unsafe_allow_html=True)

def initialize_session_state(config):
    if 'current_step' not in st.session_state:
        st.session_state.current_step = 0
    if 'input_text' not in st.session_state:
        st.session_state.input_text = ""
    if 'user_name' not in st.session_state:
        st.session_state.user_name = ""
    if 'config' not in st.session_state:
        st.session_state.config = config

def display_text_input(label, value="", height=100):
    return st.text_area(label, value=value, height=height)

def display_file_uploader(label, type=None):
    return st.file_uploader(label, type=type)

def display_audio_input(input_method):
    if input_method == "Upload audio":
        return st.file_uploader("Upload een audiobestand", type=st.session_state.config['ALLOWED_AUDIO_EXTENSIONS'])
    elif input_method == "Neem audio op":
        return st.audio_recorder(
            "Klik om audio op te nemen",
            "Opname starten",
            "Opname stoppen"
        )

def display_summary_buttons():
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Download als Word"):
            # Implement Word document creation and download here
            st.info("Word document download nog niet geïmplementeerd.")
    with col2:
        if st.button("Kopieer naar klembord"):
            # Implement clipboard copy functionality here
            st.info("Kopiëren naar klembord nog niet geïmplementeerd.")
