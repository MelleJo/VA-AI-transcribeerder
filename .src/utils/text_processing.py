from datetime import datetime
import streamlit as st

def update_gesprekslog(transcript, summary):
    if 'gesprekslog' not in st.session_state:
        st.session_state.gesprekslog = []
    
    st.session_state.gesprekslog.append({
        "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "transcript": transcript,
        "summary": summary
    })

def load_prompt(file_path):
    with open(file_path, 'r', encoding='utf-8') as file:
        return file.read()