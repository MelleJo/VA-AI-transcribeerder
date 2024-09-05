import streamlit as st
import base64
from typing import Callable
import re
from st_copy_to_clipboard import st_copy_to_clipboard
import base64
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
            st.markdown('<div class="horizontal-button-container">', unsafe_allow_html=True)
            for button in buttons:
                button()
            st.markdown('</div>', unsafe_allow_html=True)

def ui_button(label: str, on_click: Callable, key: str, primary: bool = False):
    button_class = "ui-button-primary" if primary else "ui-button-secondary"
    return st.button(label, on_click=on_click, key=key, help=f"Klik om {label.lower()}", use_container_width=False)

def ui_download_button(label: str, data: str, file_name: str, mime_type: str):
    b64 = base64.b64encode(data.encode()).decode()
    href = f'<a href="data:{mime_type};base64,{b64}" download="{file_name}" class="ui-button-secondary">{label}</a>'
    st.markdown(href, unsafe_allow_html=True)

def ui_copy_button(markdown_text: str, label: str = "Kopiëren"):
    # Convert Markdown to HTML
    html_content = markdown2.markdown(markdown_text)
    
    # Encode the HTML content
    encoded_html = base64.b64encode(html_content.encode()).decode()

    # Create a data URL
    data_url = f"data:text/html;base64,{encoded_html}"

    # JavaScript to handle copying
    js_code = f"""
    <script>
    function copyFormattedText() {{
        const listener = function(e) {{
            e.clipboardData.setData("text/html", atob("{encoded_html}"));
            e.clipboardData.setData("text/plain", document.getElementById("formatted-content").innerText);
            e.preventDefault();
        }};
        document.addEventListener("copy", listener);
        document.execCommand("copy");
        document.removeEventListener("copy", listener);
        alert("Gekopieerd! De opmaak blijft behouden bij het plakken in een teksteditor die opmaak ondersteunt.");
    }}
    </script>
    """

    # HTML for the button and hidden content
    button_html = f"""
    <button onclick="copyFormattedText()" style="font-size: 16px; padding: 10px 20px; background-color: #4CAF50; color: white; border: none; border-radius: 5px; cursor: pointer;">
        {label}
    </button>
    <div id="formatted-content" style="display: none;">
        {html_content}
    </div>
    """

    # Combine JavaScript and HTML
    full_html = js_code + button_html

    # Render the HTML
    st.components.v1.html(full_html, height=50)

    # Provide a link for browsers that don't support copying
    st.markdown(f'<a href="{data_url}" download="formatted_text.html" style="display: none;">Backup Download Link</a>', unsafe_allow_html=True)

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