import streamlit as st
import base64
from typing import Callable
import re

def ui_card(title: str, content: str, buttons: list[Callable] = None):
    with st.container():
        st.markdown(f"""
        <div class="ui-card">
            <h3>{title}</h3>
            <div class="ui-card-content">{content}</div>
        </div>
        """, unsafe_allow_html=True)
        
        if buttons:
            cols = st.columns(len(buttons))
            for i, button in enumerate(buttons):
                with cols[i]:
                    button()

def ui_button(label: str, on_click: Callable, key: str, primary: bool = False):
    button_class = "ui-button-primary" if primary else "ui-button-secondary"
    return st.button(label, on_click=on_click, key=key, help=f"Klik om {label.lower()}", use_container_width=True)

def ui_download_button(label: str, data: str, file_name: str, mime_type: str):
    b64 = base64.b64encode(data.encode()).decode()
    href = f'<a href="data:{mime_type};base64,{b64}" download="{file_name}" class="ui-button-secondary">{label}</a>'
    st.markdown(href, unsafe_allow_html=True)

def ui_copy_button(text: str, label: str = "Kopiëren"):
    st.code(text)
    st.button(label, key=f"copy_{hash(text)}", on_click=lambda: st.write("Gekopieerd naar klembord!"))

def ui_expandable_text_area(label: str, text: str, max_lines: int = 5):
    placeholder = st.empty()
    
    # Calculate the number of lines in the text
    num_lines = text.count('\n') + 1
    
    if num_lines > max_lines:
        truncated_text = '\n'.join(text.split('\n')[:max_lines]) + '...'
        
        # Create a unique key for this instance
        expand_key = f"expand_{hash(text)}"
        
        if expand_key not in st.session_state:
            st.session_state[expand_key] = False
        
        if not st.session_state[expand_key]:
            placeholder.text_area(label, truncated_text, height=150, disabled=True)
            if st.button("Toon meer", key=f"show_more_{hash(text)}"):
                st.session_state[expand_key] = True
        else:
            placeholder.text_area(label, text, height=300, disabled=True)
            if st.button("Toon minder", key=f"show_less_{hash(text)}"):
                st.session_state[expand_key] = False
    else:
        placeholder.text_area(label, text, height=150, disabled=True)

def sanitize_html(text: str) -> str:
    """Remove HTML tags from the given text."""
    return re.sub('<[^<]+?>', '', text)

def apply_custom_css():
    """Load and apply custom CSS"""
    with open('static/styles.css', 'r') as f:
        custom_css = f.read()
    st.markdown(f'<style>{custom_css}</style>', unsafe_allow_html=True)