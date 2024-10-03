import streamlit as st
import base64

def apply_custom_css():
    """
    Apply custom CSS to the Streamlit app.
    """
    with open('static/styles.css', 'r') as f:
        custom_css = f.read()
    st.markdown(f'<style>{custom_css}</style>', unsafe_allow_html=True)

def ui_card(title, content, buttons=None):
    """
    Create a custom UI card.
    
    Args:
        title (str): The card title.
        content (str): The card content.
        buttons (list): Optional list of button functions.
    """
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

def ui_button(label, on_click, key, primary=False, disabled=False):
    """
    Create a custom UI button.
    
    Args:
        label (str): The button label.
        on_click (function): The function to call when the button is clicked.
        key (str): A unique key for the button.
        primary (bool): Whether this is a primary button.
        disabled (bool): Whether the button should be disabled.
    
    Returns:
        bool: True if the button was clicked, False otherwise.
    """
    button_class = "ui-button-primary" if primary else "ui-button-secondary"
    return st.button(label, on_click=on_click, key=key, help=f"Klik om {label.lower()}", use_container_width=True, disabled=disabled)

def ui_info_box(content, type="info"):
    """
    Create a custom info box.
    
    Args:
        content (str): The content of the info box.
        type (str): The type of info box (info, success, warning, error).
    """
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

def ui_progress_bar(progress, label=""):
    """
    Create a custom progress bar.
    
    Args:
        progress (float): The progress value (0.0 to 1.0).
        label (str): Optional label for the progress bar.
    """
    st.markdown(f"""
    <div style="background-color: #f0f0f0; border-radius: 5px; padding: 1px;">
        <div style="background-color: #4CAF50; width: {progress*100}%; height: 20px; border-radius: 5px; text-align: center; line-height: 20px; color: white;">
            {label}
        </div>
    </div>
    """, unsafe_allow_html=True)

def ui_chat_message(role, content):
    """
    Create a chat message UI component.
    
    Args:
        role (str): The role of the message sender (user or assistant).
        content (str): The content of the message.
    """
    with st.chat_message(role):
        st.markdown(content)

def ui_audio_recorder():
    """
    Create an audio recorder UI component.
    
    Returns:
        dict: Audio data if recorded, None otherwise.
    """
    return st.audio_recorder(key="audio_recorder", start_prompt="Start opname", stop_prompt="Stop opname")

def ui_file_uploader(label, accepted_types):
    """
    Create a file uploader UI component.
    
    Args:
        label (str): The label for the file uploader.
        accepted_types (list): List of accepted file types.
    
    Returns:
        UploadedFile: The uploaded file object.
    """
    return st.file_uploader(label, type=accepted_types)

def ui_text_input(label, key, value=""):
    """
    Create a text input UI component.
    
    Args:
        label (str): The label for the text input.
        key (str): A unique key for the input.
        value (str): The initial value of the input.
    
    Returns:
        str: The input value.
    """
    return st.text_input(label, key=key, value=value)

def ui_text_area(label, key, value="", height=150):
    """
    Create a text area UI component.
    
    Args:
        label (str): The label for the text area.
        key (str): A unique key for the text area.
        value (str): The initial value of the text area.
        height (int): The height of the text area in pixels.
    
    Returns:
        str: The text area value.
    """
    return st.text_area(label, key=key, value=value, height=height)