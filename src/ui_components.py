# src/ui_components.py

import streamlit as st

def apply_custom_css():
    with open('static/styles.css') as f:
        st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)

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