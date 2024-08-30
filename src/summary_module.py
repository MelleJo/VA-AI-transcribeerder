# src/summary_module.py

import streamlit as st
from openai import OpenAI
from src.config import SUMMARY_MODEL, MAX_TOKENS, TEMPERATURE, OPENAI_API_KEY

client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

def generate_summary(input_text, prompt):
    try:
        response = client.chat.completions.create(
            model=SUMMARY_MODEL,
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": input_text}
            ],
            max_tokens=MAX_TOKENS,
            n=1,
            stop=None,
            temperature=TEMPERATURE,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        st.error(f"Er is een fout opgetreden bij het genereren van de samenvatting: {str(e)}")
        return None

def render_summary_generation():
    st.header("Stap 3: Samenvatting Genereren")

    if not st.session_state.input_text:
        st.warning("Voer eerst tekst in bij Stap 1 voordat u een samenvatting genereert.")
        return

    if not st.session_state.selected_prompt:
        st.warning("Selecteer eerst een prompt bij Stap 2 voordat u een samenvatting genereert.")
        return

    if st.button("Genereer Samenvatting", key="generate_summary_button"):
        with st.spinner("Samenvatting wordt gegenereerd..."):
            summary = generate_summary(st.session_state.input_text, st.session_state.selected_prompt)
            if summary:
                st.session_state.summary = summary
                st.success("Samenvatting succesvol gegenereerd!")
                st.markdown("### Gegenereerde Samenvatting")
                st.markdown(summary)
            else:
                st.error("Samenvatting genereren mislukt. Probeer het opnieuw.")

    if st.session_state.summary:
        st.markdown("### Definitieve Samenvatting")
        st.markdown(st.session_state.summary)