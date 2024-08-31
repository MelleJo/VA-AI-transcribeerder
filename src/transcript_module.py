# src/transcript_module.py

import streamlit as st

def render_transcript_edit():
    st.header("Stap 3: Transcript bewerken")
    
    if not st.session_state.input_text:
        st.warning("Er is geen transcript om te bewerken. Ga terug naar de vorige stap om tekst in te voeren.")
        return

    st.markdown("### Bewerk het transcript")
    st.session_state.input_text = st.text_area("Transcript:", value=st.session_state.input_text, height=400)

    if st.button("Bevestig transcript"):
        if st.session_state.input_text:
            st.success("Transcript bevestigd. Klik op 'Genereer Samenvatting' om door te gaan.")
        else:
            st.warning("Het transcript mag niet leeg zijn.")