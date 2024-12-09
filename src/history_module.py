# src/history_module.py

import streamlit as st
import pandas as pd
from io import BytesIO
import datetime
from .ui_components import ui_styled_button

def add_to_history(prompt, input_text, summary):
    if 'history' not in st.session_state:
        st.session_state.history = []
    
    st.session_state.history.append({
        'timestamp': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        'prompt': prompt,
        'input_text': input_text,
        'summary': summary
    })

def render_history():
    st.header("Geschiedenis - let op: dit is nog een zeer experimentele functie")

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

    if ui_styled_button("Download geschiedenis als CSV", on_click=download_history_as_csv, key="download_csv_button"):
        pass

    if ui_styled_button("Wis geschiedenis", on_click=clear_history, key="clear_history_button"):
        pass

    if ui_styled_button("Terug naar instructie selecteren", on_click=return_to_instructions, key="return_instructions_button"):
        pass

def download_history_as_csv():
    df = pd.DataFrame(st.session_state.history)
    csv = df.to_csv(index=False)
    b = BytesIO()
    b.write(csv.encode())
    b.seek(0)
    st.download_button(
        label="Download CSV",
        data=b,
        file_name="gesprekssamenvatter_geschiedenis.csv",
        mime="text/csv"
    )

def clear_history():
    st.session_state.history = []
    st.success("Geschiedenis is gewist.")
    st.rerun()

def return_to_instructions():
    st.session_state.step = 1
    st.rerun()
