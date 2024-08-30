# src/output_module.py

import streamlit as st
from src import utils
from st_copy_to_clipboard import st_copy_to_clipboard

def render_output():
    st.header("Step 4: Output")

    if not st.session_state.summary:
        st.warning("No summary has been generated yet. Please complete the previous steps.")
        return

    st.markdown("### Final Summary")
    st.text_area("", value=st.session_state.summary, height=300, disabled=True)

    col1, col2 = st.columns(2)
    
    with col1:
        if st_copy_to_clipboard(st.session_state.summary):
            st.success("Summary copied to clipboard!")

    with col2:
        if st.download_button(
            label="Download Summary",
            data=st.session_state.summary,
            file_name="generated_summary.txt",
            mime="text/plain"
        ):
            st.success("Summary downloaded successfully!")

    st.markdown("### Feedback")
    feedback = st.text_area("Please provide any feedback or suggestions for improvement:", height=100)
    if st.button("Submit Feedback"):
        # Here you can implement logic to save or send the feedback
        st.success("Thank you for your feedback!")

    if st.button("Start New Summary"):
        for key in ['input_text', 'selected_prompt', 'summary']:
            if key in st.session_state:
                del st.session_state[key]
        st.session_state.step = 1
        st.rerun()