# src/ui_components.py

import streamlit as st

def apply_custom_css():
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600&display=swap');

    body {
        font-family: 'Inter', sans-serif;
        background-color: #f8fafc;
    }

    .stApp {
        max-width: 1200px;
        margin: 0 auto;
    }

    h1, h2, h3 {
        color: #1e293b;
    }

    .stButton>button {
        background-color: #3B82F6;
        color: white;
        border-radius: 6px;
        border: none;
        padding: 0.5rem 1rem;
        font-weight: 600;
    }

    .stButton>button:hover {
        background-color: #2563eb;
    }

    .stTextInput>div>div>input {
        border-radius: 6px;
    }

    .stSelectbox>div>div>select {
        border-radius: 6px;
    }
    </style>
    """, unsafe_allow_html=True)

def create_card(title, content, key):
    st.markdown(f"""
    <div style="
        background-color: white;
        border-radius: 8px;
        padding: 1rem;
        margin-bottom: 1rem;
        box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.1), 0 1px 2px 0 rgba(0, 0, 0, 0.06);
    ">
        <h3 style="margin-top: 0;">{title}</h3>
        <p>{content}</p>
    </div>
    """, unsafe_allow_html=True)
    return st.button(f"Select {title}", key=key)