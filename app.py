import streamlit as st
from src import config, prompt_module, input_module, transcript_module, summary_and_output_module, ui_components, history_module
from src.utils import post_process_grammar_check, format_currency, transcribe_audio, process_text_file
import logging
import os
import uuid
from openai import OpenAI
from streamlit_mic_recorder import mic_recorder
import tempfile

logging.getLogger('watchdog').setLevel(logging.ERROR)

def load_css():
    css_path = os.path.join('static', 'styles.css')
    with open(css_path) as f:
        return f'<style>{f.read()}</style>'

def main():
    st.set_page_config(page_title="Samenvatter", layout="wide")

    # Apply custom CSS
    st.markdown(load_css(), unsafe_allow_html=True)
    ui_components.apply_custom_css()

    # Initialize OpenAI client
    client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

    # Header
    st.markdown("""
    <div class="header">
        <h1 class="app-name">Samenvatter</h1>
    </div>
    """, unsafe_allow_html=True)

    # Initialize session state
    if 'step' not in st.session_state:
        st.session_state.step = 1
    if 'messages' not in st.session_state:
        st.session_state.messages = []
    if 'input_text' not in st.session_state:
        st.session_state.input_text = ""
    if 'selected_prompt' not in st.session_state:
        st.session_state.selected_prompt = None
    if 'summary' not in st.session_state:
        st.session_state.summary = ""

    # Main content
    st.markdown("<h2 class='main-prompt'>Wat wil je doen?</h2>", unsafe_allow_html=True)
    st.markdown("<p class='sub-prompt'>Selecteer een prompt, neem audio op, of upload een bestand.</p>", unsafe_allow_html=True)

    # Display chat messages
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # Step 1: Prompt Selection
    if st.session_state.step == 1:
        prompts = prompt_module.get_prompt_names()
        selected_prompt = st.selectbox("Kies een instructieset:", prompts)
        if selected_prompt:
            st.session_state.selected_prompt = selected_prompt
            st.session_state.messages.append({"role": "assistant", "content": f"Je hebt '{selected_prompt}' geselecteerd. Je kunt nu audio opnemen of een bestand uploaden."})
            st.session_state.step = 2
            st.rerun()

    # Step 2: Input Handling
    elif st.session_state.step == 2:
        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button("🎤 Audio opnemen"):
                st.session_state.messages.append({"role": "user", "content": "Ik wil audio opnemen."})
                audio_data = mic_recorder(key="recorder", start_prompt="Start opname", stop_prompt="Stop opname")
                if isinstance(audio_data, dict) and 'bytes' in audio_data:
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as temp_audio:
                        temp_audio.write(audio_data['bytes'])
                        st.session_state.input_text = transcribe_audio(temp_audio.name)
                    st.session_state.messages.append({"role": "assistant", "content": "Audio is succesvol opgenomen en getranscribeerd."})
                    st.session_state.step = 3
                    st.rerun()
        
        with col2:
            uploaded_file = st.file_uploader("📁 Upload bestand", type=config.ALLOWED_AUDIO_TYPES + config.ALLOWED_TEXT_TYPES)
            if uploaded_file:
                st.session_state.messages.append({"role": "user", "content": f"Ik heb een bestand geüpload: {uploaded_file.name}"})
                if uploaded_file.type in config.ALLOWED_AUDIO_TYPES:
                    with tempfile.NamedTemporaryFile(delete=False, suffix="." + uploaded_file.type.split("/")[-1]) as temp_file:
                        temp_file.write(uploaded_file.getvalue())
                        st.session_state.input_text = transcribe_audio(temp_file.name)
                else:
                    st.session_state.input_text = process_text_file(uploaded_file)
                st.session_state.messages.append({"role": "assistant", "content": "Bestand is succesvol verwerkt."})
                st.session_state.step = 3
                st.rerun()
        
        with col3:
            if st.button("✍️ Tekst invoeren"):
                st.session_state.messages.append({"role": "user", "content": "Ik wil tekst invoeren."})
                st.session_state.step = 2.5
                st.rerun()

    # Step 2.5: Text Input
    elif st.session_state.step == 2.5:
        st.session_state.input_text = st.text_area("Voer je tekst in:", height=200)
        if st.button("Bevestig tekst"):
            st.session_state.messages.append({"role": "assistant", "content": "Tekst is succesvol ingevoerd."})
            st.session_state.step = 3
            st.rerun()

    # Step 3: Transcript Editing
    elif st.session_state.step == 3:
        st.session_state.input_text = st.text_area("Bewerk het transcript indien nodig:", value=st.session_state.input_text, height=300)
        if st.button("Bevestig transcript"):
            st.session_state.messages.append({"role": "assistant", "content": "Transcript is bevestigd. Ik ga nu een samenvatting genereren."})
            st.session_state.step = 4
            st.rerun()

    # Step 4: Summary Generation
    elif st.session_state.step == 4:
        if not st.session_state.summary:
            with st.spinner("Samenvatting wordt gegenereerd..."):
                prompt_content = prompt_module.get_prompt_content(st.session_state.selected_prompt)
                st.session_state.summary = summary_and_output_module.generate_summary(st.session_state.input_text, config.BASE_PROMPT, prompt_content)
        
        st.markdown("### Samenvatting")
        st.markdown(st.session_state.summary)
        st.session_state.messages.append({"role": "assistant", "content": "Hier is de gegenereerde samenvatting. Wat wil je hiermee doen?"})

        if st.button("Download als Word"):
            summary_and_output_module.export_to_docx(st.session_state.summary)
        if st.button("Download als PDF"):
            summary_and_output_module.export_to_pdf(st.session_state.summary)
        if st.button("Samenvatting aanpassen"):
            st.session_state.step = 4.5
            st.rerun()
        if st.button("Nieuwe samenvatting"):
            st.session_state.step = 1
            st.session_state.input_text = ""
            st.session_state.summary = ""
            st.session_state.messages = []
            st.rerun()

    # Step 4.5: Summary Customization
    elif st.session_state.step == 4.5:
        customization_request = st.text_area("Hoe wil je de samenvatting aanpassen?")
        if st.button("Pas samenvatting aan"):
            with st.spinner("Samenvatting wordt aangepast..."):
                st.session_state.summary = summary_and_output_module.customize_summary(st.session_state.summary, customization_request, st.session_state.input_text)
            st.session_state.messages.append({"role": "assistant", "content": "De samenvatting is aangepast. Hier is het resultaat."})
            st.session_state.step = 4
            st.rerun()

    # Add to history
    if st.session_state.step == 4 and st.session_state.summary:
        history_module.add_to_history(st.session_state.selected_prompt, st.session_state.input_text, st.session_state.summary)

    # Footer
    st.markdown("---")
    if st.button("Bekijk geschiedenis"):
        st.session_state.step = 5
        st.rerun()

    # Step 5: History
    if st.session_state.step == 5:
        history_module.render_history()
        if st.button("Terug naar start"):
            st.session_state.step = 1
            st.session_state.input_text = ""
            st.session_state.summary = ""
            st.session_state.messages = []
            st.rerun()

if __name__ == "__main__":
    main()