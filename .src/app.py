import streamlit as st
import os
import logging
from utils.audio_processing import process_audio_input
from services.summarization_service import run_summarization
from utils.file_processing import process_uploaded_file
from ui.pages import render_feedback_form, render_conversation_history, setup_page_style
from ui.components import initialize_session_state
from config import BASE_DIR, load_config

# Load configurations from config.py
config = load_config()

logger = logging.getLogger(__name__)

# Set the page configuration
st.set_page_config(page_title="Gesprekssamenvatter", page_icon="🎙️", layout="wide")

def main():
    setup_page_style()
    initialize_session_state()

    # Direct prompt selection process
    st.header("Selecteer een prompt")

    # Load all prompt files from the prompts directory
    prompt_files = [f for f in os.listdir(config['PROMPTS_DIR']) if f.endswith('.txt')]

    # If there are no prompt files, display an error
    if not prompt_files:
        st.error("Geen prompt bestanden gevonden in de opgegeven map.")
        return

    # Select a prompt from a dropdown list
    selected_prompt = st.selectbox("Selecteer een prompt", prompt_files)

    # Display selected prompt
    st.write(f"Geselecteerde prompt: {selected_prompt}")

    if selected_prompt:
        # Load the content of the selected prompt
        prompt_path = os.path.join(config['PROMPTS_DIR'], selected_prompt)
        with open(prompt_path, "r", encoding="utf-8") as file:
            prompt_content = file.read()

        # Display the prompt content for confirmation
        st.write(f"**Inhoud van de geselecteerde prompt:**\n\n{prompt_content}")

        # Process the selected prompt with the input methods
        st.session_state.selected_prompt_content = prompt_content  # Store the prompt content in session state

        # Example to proceed with audio input processing
        input_method = st.selectbox("Selecteer invoermethode", config['INPUT_METHODS'])

        if input_method == "Upload audio":
            audio_file = st.file_uploader("Upload een audio bestand", type=['mp3', 'wav', 'ogg'])
            if audio_file is not None:
                with st.spinner("Bezig met het verwerken van audio..."):
                    transcript = process_audio_input(audio_file, prompt_content)
                    st.session_state.transcript = transcript

                    if st.button("Genereer samenvatting"):
                        summary = run_summarization(transcript, st.session_state.prompt_name, st.session_state.user_name)
                        st.session_state.summary = summary
                        st.write("**Samenvatting:**")
                        st.write(summary)

    st.markdown("---")
    st.markdown("### Extra opties")

    tab1, tab2 = st.tabs(["Geef feedback", "Bekijk gespreksgeschiedenis"])

    with tab1:
        render_feedback_form()

    with tab2:
        render_conversation_history()


if __name__ == "__main__":
    main()
