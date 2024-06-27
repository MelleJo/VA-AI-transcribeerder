import streamlit as st
from services.email_service import send_feedback_email
import html

def render_feedback_form():
    with st.expander("Geef feedback"):
        with st.form(key="feedback_form"):
            user_first_name = st.text_input("Uw voornaam (verplicht bij feedback):")
            feedback = st.radio("Was dit antwoord nuttig?", ["Positief", "Negatief"])
            additional_feedback = st.text_area("Laat aanvullende feedback achter:")
            submit_button = st.form_submit_button(label="Verzenden")

            if submit_button:
                if not user_first_name:
                    st.warning("Voornaam is verplicht bij het geven van feedback.", icon="⚠️")
                else:
                    success = send_feedback_email(
                        transcript=st.session_state.get('transcript', ''),
                        summary=st.session_state.get('summary', ''),
                        feedback=feedback,
                        additional_feedback=additional_feedback,
                        user_first_name=user_first_name
                    )
                    if success:
                        st.success("Bedankt voor uw feedback!")
                    else:
                        st.error("Er is een fout opgetreden bij het verzenden van de feedback. Probeer het later opnieuw.")

def render_conversation_history():
    st.subheader("Laatste vijf gesprekken")
    for i, gesprek in enumerate(st.session_state.get('gesprekslog', [])):
        with st.expander(f"Gesprek {i+1} op {gesprek['time']}"):
            st.markdown("**Transcript:**")
            st.markdown(f'<div class="content">{html.escape(gesprek["transcript"])}</div>', unsafe_allow_html=True)
            st.markdown("**Samenvatting:**")
            st.markdown(gesprek["summary"], unsafe_allow_html=True)