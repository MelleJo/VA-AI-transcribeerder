import streamlit as st
from src.ui_components import ui_styled_button, ui_info_box

def render_transcript_edit():
    st.header("Stap 3: Transcript bewerken")
    
    st.write("Transcription complete:", st.session_state.get('transcription_complete', False))
    st.write("Input text available:", 'input_text' in st.session_state)
    if 'input_text' in st.session_state:
        st.write("Transcript lengte:", len(st.session_state.input_text))
        st.write("Eerste 100 karakters van transcript:", st.session_state.input_text[:100])
    
    if not st.session_state.input_text:
        ui_info_box("Er is geen transcript om te bewerken. Ga terug naar de vorige stap om tekst in te voeren.", "warning")
        return

    st.markdown("### Bewerk het transcript")
    st.session_state.input_text = st.text_area("Transcript:", value=st.session_state.input_text, height=400)

    if ui_styled_button("Bevestig transcript", on_click=None, key="confirm_transcript_button", is_active=True):
        if st.session_state.input_text:
            ui_info_box("Transcript bevestigd. Klik op 'Genereer Samenvatting' om door te gaan.", "success")
            st.session_state.transcript_confirmed = True
        else:
            ui_info_box("Het transcript mag niet leeg zijn.", "warning")

    if st.session_state.get('transcript_confirmed', False):
        if ui_styled_button("Genereer Samenvatting", on_click=lambda: setattr(st.session_state, 'step', st.session_state.step + 1), key="generate_summary_button", is_active=True, primary=True):
            st.session_state.step += 1
            st.rerun()
    else:
        ui_styled_button("Genereer Samenvatting", on_click=None, key="generate_summary_button", is_active=False)