import streamlit as st
import base64
from typing import Callable
import re
from st_copy_to_clipboard import st_copy_to_clipboard
import markdown2

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

def ui_button(label: str, on_click: Callable, key: str, primary: bool = False, disabled: bool = False):
    button_class = "ui-button-primary" if primary else "ui-button-secondary"
    return st.button(label, on_click=on_click, key=key, help=f"Klik om {label.lower()}", use_container_width=True, disabled=disabled)

def ui_download_button(label: str, data: str, file_name: str, mime_type: str):
    b64 = base64.b64encode(data.encode()).decode()
    href = f'<a href="data:{mime_type};base64,{b64}" download="{file_name}" class="ui-button-secondary">{label}</a>'
    st.markdown(href, unsafe_allow_html=True)

def ui_copy_button(text: str, label: str = "Kopiëren"):
    button_id = f"copy_button_{hash(text)}"
    st.markdown(f"""
    <button id="{button_id}" class="css-16u8z0w edgvbvh10">
        {label}
    </button>
    <script>
        const btn = document.getElementById('{button_id}');
        btn.addEventListener('click', function() {{
            navigator.clipboard.writeText(`{text}`).then(function() {{
                btn.textContent = 'Gekopieerd!';
                setTimeout(() => btn.textContent = '{label}', 2000);
            }}).catch(function(err) {{
                console.error('Kon niet kopiëren: ', err);
            }});
        }});
    </script>
    """, unsafe_allow_html=True)

def ui_expandable_text_area(label: str, text: str, max_lines: int = 5):
    placeholder = st.empty()
    
    num_lines = text.count('\n') + 1
    
    if num_lines > max_lines:
        truncated_text = '\n'.join(text.split('\n')[:max_lines]) + '...'
        
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
    return re.sub('<[^<]+?>', '', text)

def apply_custom_css():
    with open('static/styles.css', 'r') as f:
        custom_css = f.read()
    st.markdown(f'<style>{custom_css}</style>', unsafe_allow_html=True)

def style_button(label: str, is_active: bool, key: str = None):
    color = "#4CAF50" if is_active else "#cccccc"
    button_key = f" key='{key}'" if key else ""
    return f"""
    <style>
    div.stButton > button{button_key} {{
        background-color: {color} !important;
        color: {"white" if is_active else "black"} !important;
        border-color: {color} !important;
    }}
    div.stButton > button{button_key}:hover {{
        background-color: {"#45a049" if is_active else "#b3b3b3"} !important;
        border-color: {"#45a049" if is_active else "#b3b3b3"} !important;
    }}
    </style>
    """

def ui_styled_button(label: str, on_click: Callable, key: str, is_active: bool = True, primary: bool = False):
    st.markdown(style_button(label, is_active, key), unsafe_allow_html=True)
    return st.button(label, on_click=on_click, key=key, disabled=not is_active, use_container_width=True)

def ui_info_box(content: str, type: str = "info"):
    colors = {
        "info": "#e7f3fe",
        "success": "#ddffdd",
        "warning": "#ffffcc",
        "error": "#ffdddd"
    }
    icons = {
        "info": "ℹ️",
        "success": "✅",
        "warning": "⚠️",
        "error": "❌"
    }
    st.markdown(f"""
    <div style="background-color: {colors[type]}; padding: 10px; border-radius: 5px; margin-bottom: 10px;">
        <p style="margin: 0;"><strong>{icons[type]} {type.capitalize()}:</strong> {content}</p>
    </div>
    """, unsafe_allow_html=True)

def ui_progress_bar(progress: float, label: str = ""):
    st.markdown(f"""
    <div style="background-color: #f0f0f0; border-radius: 5px; padding: 1px;">
        <div style="background-color: #4CAF50; width: {progress*100}%; height: 20px; border-radius: 5px; text-align: center; line-height: 20px; color: white;">
            {label}
        </div>
    </div>
    """, unsafe_allow_html=True)