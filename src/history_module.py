# src/history_module.py

import streamlit as st
import pandas as pd
from datetime import datetime

def add_to_history(prompt, input_text, summary):
    if 'history' not in st.session_state:
        st.session_state.history = []
    
    st.session_state.history.append({
        'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        'prompt': prompt,
        'input_text': input_text,
        'summary': summary
    })

def render_history():
    st.header("Geschiedenis")

    if not st.session_state.history:
        st.info("Er zijn nog geen samenvattingen gemaakt.")
        return

    df = pd.DataFrame(st.session_state.history)
    
    for index, row in df.iterrows():
        with st.expander(f"Samenvatting {index + 1} - {row['timestamp']}"):
            st.subheader("Prompt")
            st.write(row['prompt'])
            st.subheader("Invoertekst")
            st.write(row['input_text'][:200] + "..." if len(row['input_text']) > 200 else row['input_text'])
            st.subheader("Samenvatting")
            st.write(row['summary'])

    if st.button("Terug naar Prompt Selectie"):
        st.session_state.step = 1
        st.rerun()