# src/summary_module.py

import streamlit as st
from openai import OpenAI
from src.config import SUMMARY_MODEL, MAX_TOKENS, TEMPERATURE

client = OpenAI(api_key=config.OPENAI_API_KEY)

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
        st.error(f"An error occurred while generating the summary: {str(e)}")
        return None

def render_summary_generation():
    st.header("Step 3: Summary Generation")

    if not st.session_state.input_text:
        st.warning("Please provide input text in Step 1 before generating a summary.")
        return

    if not st.session_state.selected_prompt:
        st.warning("Please select a prompt in Step 2 before generating a summary.")
        return

    if st.button("Generate Summary"):
        with st.spinner("Generating summary..."):
            summary = generate_summary(st.session_state.input_text, st.session_state.selected_prompt)
            if summary:
                st.session_state.summary = summary
                st.success("Summary generated successfully!")
                st.markdown("### Generated Summary")
                st.text_area("", value=summary, height=300, disabled=True)
            else:
                st.error("Failed to generate summary. Please try again.")

    if st.session_state.summary:
        st.markdown("### Generated Summary")
        st.text_area("", value=st.session_state.summary, height=300, disabled=True)