import streamlit_shadcn_ui as ui
import base64
from typing import Callable, List, Dict
import re

def ui_card(title: str, content: str, buttons: List[Callable] = None):
    with ui.card(key=f"card_{title.lower().replace(' ', '_')}"):
        ui.element("h3", text=title)
        ui.element("div", text=content, className="ui-card-content")
        
        if buttons:
            for button in buttons:
                button()

def full_screen_loader(progress, message, status_updates, estimated_time):
    status_html = "".join([f"<p class='status-update {'complete' if idx <= progress // 25 else ''}'>{update}</p>" for idx, update in enumerate(status_updates)])
    overlay_html = f"""
    <div class="fullscreen-loader">
        <div class="loader-content">
            <div class="spinner"></div>
            <p>{message}</p>
            <div class="progress-container">
                <div class="progress-bar" style="width: {progress}%;"></div>
            </div>
            <p>Voortgang: {progress}%</p>
            <p>Geschatte resterende tijd: {estimated_time}</p>
            <div class="status-updates">
                {status_html}
            </div>
        </div>
    </div>
    """
    ui.element("div", text=overlay_html, unsafe_allow_html=True)

def estimate_time(file_size, current_step, total_steps, elapsed_time):
    if current_step == 0:
        return "Berekenen..."
    
    avg_time_per_step = elapsed_time / current_step
    remaining_steps = total_steps - current_step
    estimated_remaining_time = avg_time_per_step * remaining_steps
    
    size_factor = file_size / 1_000_000
    estimated_remaining_time *= (1 + (size_factor * 0.1))
    
    minutes, seconds = divmod(int(estimated_remaining_time), 60)
    return f"{minutes}m {seconds}s"

def add_loader_css():
    ui.element("style", text="""
    .fullscreen-loader {
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background-color: rgba(255, 255, 255, 0.9);
        z-index: 9999;
        display: flex;
        align-items: center;
        justify-content: center;
    }
    .loader-content {
        text-align: center;
    }
    .spinner {
        border: 8px solid #f3f3f3;
        border-top: 8px solid #3498db;
        border-radius: 50%;
        width: 80px;
        height: 80px;
        animation: spin 2s linear infinite;
        margin: 0 auto;
    }
    @keyframes spin {
        0% { transform: rotate(0deg); }
        100% { transform: rotate(360deg); }
    }
    .progress-container {
        width: 80%;
        background-color: #e0e0e0;
        border-radius: 25px;
        margin: 20px auto;
    }
    .progress-bar {
        height: 20px;
        background-color: #3498db;
        border-radius: 25px;
        width: 0%;
    }
    .status-updates {
        text-align: left;
        margin-top: 20px;
    }
    .status-update {
        margin: 5px 0;
        padding-left: 25px;
        position: relative;
    }
    .status-update::before {
        content: '⏳';
        position: absolute;
        left: 0;
    }
    .status-update.complete::before {
        content: '✅';
    }
    """, unsafe_allow_html=True)

def ui_button(label: str, on_click: Callable, key: str, primary: bool = False):
    button_class = "ui-button-primary" if primary else "ui-button-secondary"
    return ui.button(
        text=label,
        on_click=on_click,
        key=key,
        className=button_class
    )

def prompt_card(title):
    button_id = f"prompt_{title.lower().replace(' ', '_')}"
    is_clicked = ui.button(
        text=f"Selecteer {title}",
        key=button_id
    )
    ui.element("style", text=f"""
    #{button_id} {{
        background-color: #f0f0f0;
        padding: 20px;
        border-radius: 5px;
        cursor: pointer;
        text-align: center;
    }}
    #{button_id}:hover {{
        background-color: #e0e0e0;
    }}
    """, unsafe_allow_html=True)
    return is_clicked

def input_method_card(title, icon):
    button_id = f"input_{title.lower().replace(' ', '_')}"
    is_clicked = ui.button(
        text=title,
        key=button_id
    )
    ui.element("style", text=f"""
    #{button_id} {{
        background-color: #f0f0f0;
        padding: 20px;
        border-radius: 5px;
        cursor: pointer;
        text-align: center;
    }}
    #{button_id}:hover {{
        background-color: #e0e0e0;
    }}
    """, unsafe_allow_html=True)
    return is_clicked

def ui_download_button(label: str, data: str, file_name: str, mime_type: str):
    b64 = base64.b64encode(data.encode()).decode()
    href = f'<a href="data:{mime_type};base64,{b64}" download="{file_name}" class="ui-button-secondary">{label}</a>'
    ui.element("div", text=href, unsafe_allow_html=True)

def ui_card_button(title: str, description: str):
    button_id = f"card_button_{title.lower().replace(' ', '_')}"
    is_clicked = ui.button(
        text=f"{title}\n{description}",
        key=button_id
    )
    ui.element("style", text=f"""
    #{button_id} {{
        background-color: #f9f9f9;
        padding: 20px;
        border-radius: 5px;
        cursor: pointer;
        text-align: left;
    }}
    #{button_id}:hover {{
        background-color: #e9e9e9;
    }}
    """, unsafe_allow_html=True)
    return is_clicked

def ui_copy_button(text: str, label: str = "Kopiëren"):
    ui.element("code", text=text)
    ui.button(text=label, on_click=lambda: ui.element("div", text=f"Tekst gekopieerd: {text}"))

def ui_expandable_text_area(label: str, text: str, max_lines: int = 5):
    placeholder = ui.element("div")
    num_lines = text.count('\n') + 1
    
    if num_lines > max_lines:
        truncated_text = '\n'.join(text.split('\n')[:max_lines]) + '...'
        
        expand_key = f"expand_{hash(text)}"
        
        if expand_key not in ui.session_state:
            ui.session_state[expand_key] = False
        
        if not ui.session_state[expand_key]:
            placeholder.element("textarea", text=truncated_text, height=150, disabled=True)
            if ui.button("Toon meer", key=f"show_more_{hash(text)}"):
                ui.session_state[expand_key] = True
        else:
            placeholder.element("textarea", text=text, height=300, disabled=True)
            if ui.button("Toon minder", key=f"show_less_{hash(text)}"):
                ui.session_state[expand_key] = False
    else:
        placeholder.element("textarea", text=text, height=150, disabled=True)

def sanitize_html(text: str) -> str:
    return re.sub('<[^<]+?>', '', text)

def apply_custom_css():
    with open('static/styles.css', 'r') as f:
        custom_css = f.read()
    ui.element("style", text=custom_css, unsafe_allow_html=True)

def style_button(label: str, is_active: bool, key: str = None):
    color = "#4CAF50" if is_active else "#cccccc"
    button_key = f" key='{key}'" if key else ""
    ui.element("style", text=f"""
    div.stButton > button[{button_key}] {{
        background-color: {color} !important;
        color: {"white" if is_active else "black"} !important;
        border-color: {color} !important;
    }}
    div.stButton > button[{button_key}]:hover {{
        background-color: {"#45a049" if is_active else "#b3b3b3"} !important;
        border-color: {"#45a049" if is_active else "#b3b3b3"} !important;
    }}
    """, unsafe_allow_html=True)

def ui_styled_button(label: str, on_click: Callable, key: str, is_active: bool = True, primary: bool = False):
    style_button(label, is_active, key)
    # Use a lambda to ensure the function is not serialized
    return ui.button(text=label, on_click=lambda: on_click(), key=key, disabled=not is_active)

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
    ui.element("div", text=f"""
    <div style="background-color: {colors[type]}; padding: 10px; border-radius: 5px; margin-bottom: 10px;">
        <p style="margin: 0;"><strong>{icons[type]} {type.capitalize()}:</strong> {content}</p>
    </div>
    """, unsafe_allow_html=True)

def ui_progress_bar(progress: float, label: str = ""):
    ui.progress(progress)
    if label:
        ui.element("div", text=label)
