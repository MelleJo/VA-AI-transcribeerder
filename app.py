import streamlit as st
from src import config, prompt_module, input_module, transcript_module, summary_and_output_module, ui_components, history_module
from src.utils import post_process_grammar_check, format_currency
import logging
import os
import uuid
from openai import OpenAI

logging.getLogger('watchdog').setLevel(logging.ERROR)

def load_css():
    css_path = os.path.join('static', 'styles.css')
    with open(css_path) as f:
        css = f.read()
    # Adding logo style directly in the CSS loaded here
    css += "\n<style>.logo {margin-bottom: 20px;}</style>"
    return f'<style>{css}</style>'

def load_custom_spinner():
    spinner_path = os.path.join('static', 'custom_spinner.html')
    with open(spinner_path, 'r') as f:
        return f.read()

def render_step_indicator(current_step, total_steps):
    html = "<div class='step-indicator'>"
    for i in range(1, total_steps + 1):
        if i < current_step:
            html += f"<div class='step completed' title='Voltooide stap'>{i}</div>"
        elif i == current_step:
            html += f"<div class='step active' title='Huidige stap'>{i}</div>"
        else:
            html += f"<div class='step' title='Volgende stap'>{i}</div>"
    html += "</div>"
    st.markdown(html, unsafe_allow_html=True)

def main():
    st.set_page_config(page_title="Gesprekssamenvatter AI", layout="wide")

    # Apply custom CSS
    st.markdown(load_css(), unsafe_allow_html=True)
    ui_components.apply_custom_css()

    # Include custom spinner
    st.components.v1.html(load_custom_spinner(), height=0)

    # Initialize OpenAI client
    client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

    # Add JavaScript for formatted text copying
    st.markdown("""
    <script>
    function copyFormattedText(elementId) {
        const element = document.getElementById(elementId);
        const htmlContent = element.getAttribute('data-html-content');
        
        const listener = function(e) {
            e.clipboardData.setData("text/html", htmlContent);
            e.clipboardData.setData("text/plain", element.innerText);
            e.preventDefault();
        };
        
        document.addEventListener("copy", listener);
        document.execCommand("copy");
        document.removeEventListener("copy", listener);
        
        // Show success message
        const successMsg = document.createElement('div');
        successMsg.textContent = 'Gekopieerd met opmaak!';
        successMsg.style.position = 'fixed';
        successMsg.style.top = '10px';
        successMsg.style.left = '50%';
        successMsg.style.transform = 'translateX(-50%)';
        successMsg.style.backgroundColor = '#4CAF50';
        successMsg.style.color = 'white';
        successMsg.style.padding = '10px';
        successMsg.style.borderRadius = '5px';
        successMsg.style.zIndex = '9999';
        document.body.appendChild(successMsg);
        
        setTimeout(() => {
            successMsg.remove();
        }, 2000);
    }
    </script>
    """, unsafe_allow_html=True)

    # Sidebar
    with st.sidebar:
        st.image("https://via.placeholder.com/150?text=AI+Logo", width=150)
        st.markdown("<h2 class='sidebar-title'>Gesprekssamenvatter AI</h2>", unsafe_allow_html=True)
        st.markdown("<p class='sidebar-text'>Versie 0.0.2</p>", unsafe_allow_html=True)
        st.markdown("<hr>", unsafe_allow_html=True)
        st.markdown("<p class='sidebar-text'>Deze AI-assistent helpt u bij het samenvatten en analyseren van gesprekken.</p>", unsafe_allow_html=True)
        st.markdown("<hr>", unsafe_allow_html=True)
        if st.button("Over deze app", key="about_button"):
            st.markdown("""
            <div class='info-container'>
            <h3 class='section-subtitle'>Over Gesprekssamenvatter AI</h3>
            <p>Gesprekssamenvatter AI is een geavanceerde tool die gebruik maakt van kunstmatige intelligentie om gesprekken te transcriberen, analyseren en samenvatten. Of het nu gaat om klantenservice-interacties, interviews, of vergaderingen, onze AI helpt u om snel de belangrijkste punten te identificeren en actiepunten te genereren.</p>
            </div>
            """, unsafe_allow_html=True)

    # Main content
    st.markdown("<h1 class='main-title'>Gesprekssamenvatter AI</h1>", unsafe_allow_html=True)

    # Initialize session state
    if 'step' not in st.session_state:
        st.session_state.step = 1
    if 'selected_prompt' not in st.session_state:
        st.session_state.selected_prompt = None
    if 'input_text' not in st.session_state:
        st.session_state.input_text = ""
    if 'summary' not in st.session_state:
        st.session_state.summary = ""
    if 'history' not in st.session_state:
        st.session_state.history = []
    if 'is_recording' not in st.session_state:
        st.session_state.is_recording = False
    if 'transcription_complete' not in st.session_state...
        st.session_state.transcription_complete = False

    # Navigation
    steps = ["Prompt Selectie", "Invoer", "Transcript Bewerken", "Samenvatting", "Geschiedenis"]
    render_step_indicator(st.session_state.step, len(steps))

    # Display current step
    st.markdown(f"<h2 class='section-title'>Stap {st.session_state.step}: {steps[st.session_state.step - 1]}</h2>", unsafe_allow_html=True)

    # Render step content
    with st.container():
        st.markdown("<div class='main-content'>", unsafe_allow_html=True)
        if st.session_state.step == 1:
            prompt_module.render_prompt_selection()
        elif st.session_state.step == 2:
            input_module.render_input_step()
        elif st.session_state.step == 3:
            transcript_module.render_transcript_edit()
        elif st.session_state.step == 4:
            summary_and_output_module.render_summary_and_output()
        elif st.session_state.step == 5:
            history_module.render_history()
        st.markdown("</div>", unsafe_allow_html=True)

    # Navigation buttons
    st.markdown("<div class='nav-buttons'>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 2, 1])
    with col1:
        if st.session_state.step > 1:
            st.markdown("""
            <div class="tooltip">
                <button class="stButton" onclick="document.getElementById('previous_button').click()">
                    ◀ Vorige
                </button>
                <span class="tooltiptext">Ga terug naar de vorige stap</span>
            </div>
            """, unsafe_allow_html=True)
            if st.button("◀ Vorige", key="previous_button", style="display: none;"):
                if st.session_state.is_recording:
                    st.warning("Stop eerst de opname voordat u teruggaat.")
                else:
                    st.session_state.step -= 1
                    st.rerun()

    with col3:
        if st.session_state.step < len(steps):
            next_label = "Volgende ▶" if st.session_state.step < 4 else "Bekijk Geschiedenis ▶"
            tooltip_text = "Ga naar de volgende stap" if st.session_state.step < 4 else "Bekijk de geschiedenis van uw samenvattingen"
            st.markdown(f"""
            <div class="tooltip">
                <button class="stButton" onclick="document.getElementById('next_button_{st.session_state.step}").click()">
                    {next_label}
                </button>
                <span class="tooltiptext">{tooltip_text}"</span>
            </div>
            """, unsafe_allow_html=True)
            if st.button(next_label, key=f"next_button_{st.session_state.step}", style="display: none;"):
                if st.session_state.is_recording:
                    st.warning("Stop eerst de opname voordat u verdergaat.")
                elif st.session_state.step == 2 en not st.session_state.transcription_complete:
                    st.warning("Verwerk eerst de input door op 'Stop opname' te klikken en het transcript te laten genereren.")
                else:
                    st.session_state.step += 1
                    st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

    # Debug Info Expander
    with st.expander("Debug Info"):
        st.markdown("<div class='info-container'>", unsafe_allow_html=True)
        st.markdown("<h3 class='section-subtitle'>Debug Informatie</h3>", unsafe_allow_html=True)
        st.markdown("<div class='info-text'>", unsafe_allow_html=True)
        st.write(f"Stap: {st.session_state.step}")
        st.write(f"Geselecteerde Prompt: {st.session_state.selected_prompt}")
        st.write(f"Invoertekst Lengte: {len(st.session_state.input_text)}")
        st.write(f"Samenvatting Lengte: {len(st.session_state.summary)}")
        st.write(f"Geschiedenis Items: {len(st.session_state.history)}")
        st.write(f"Is Opname Bezig: {st.session_state.is_recording}")
        st.write(f"Transcriptie Voltooid: {st.session_state.transcription_complete}")
        st.markdown("</div>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

if __name__ == "__main__":
    main()
