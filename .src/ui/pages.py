import streamlit as st
from st_copy_to_clipboard import st_copy_to_clipboard

from streamlit_antd.tabs import st_antd_tabs
from streamlit_antd.cascader import st_antd_cascader
from streamlit_antd.result import Action, st_antd_result
from streamlit_antd.breadcrumb import st_antd_breadcrumb
from streamlit_antd.cards import Action as CardAction, Item, st_antd_cards
#from streamlit_antd.select import st_antd_select
#from streamlit_antd.button import st_antd_button

#from components.fancy_select import fancy_select
from ui.components import display_transcript, display_summary, display_text_input, display_file_uploader
from services.email_service import send_feedback_email
from services.summarization_service import run_summarization
from utils.audio_processing import process_audio_input as utils_process_audio_input
from utils.file_processing import process_uploaded_file
from utils.text_processing import update_gesprekslog

from streamlit_extras.switch_page_button import switch_page
from streamlit_extras.colored_header import colored_header
from streamlit_extras.add_vertical_space import add_vertical_space
from streamlit_extras.stylable_container import stylable_container


def render_wizard():
    st.title("Gesprekssamenvatter")

    steps = ["Bedrijfsonderdeel", "Afdeling", "Gesprekstype", "Invoermethode", "Samenvatting"]
    current_step = st.session_state.get('current_step', 0)

    # Progress bar
    st.progress((current_step) / (len(steps) - 1))

    # Render current step
    if current_step == 0:
        render_business_side_selection()
    elif current_step == 1:
        render_department_selection()
    elif current_step == 2:
        render_conversation_type_selection()
    elif current_step == 3:
        render_input_method_selection()
    elif current_step == 4:
        render_summary()

    # Bottom navigation
    col1, col2, col3 = st.columns([1, 3, 1])
    with col1:
        if current_step > 0:
            if st.button("◀ Terug", key="back", help="Ga terug naar de vorige stap"):
                st.session_state.current_step -= 1
                st.rerun()

    with col3:
        if current_step < len(steps) - 1:
            if st.button("Volgende ▶", key="next", help="Ga naar de volgende stap"):
                if validate_step(current_step):
                    st.session_state.current_step += 1
                    st.rerun()
                else:
                    st.warning("Maak eerst een selectie voordat u verdergaat.")

def render_business_side_selection():
    st.header("Selecteer het bedrijfsonderdeel")
    
    for side in st.session_state.BUSINESS_SIDES.keys():
        if st.button(side, key=f"business_side_{side}"):
            st.session_state.business_side = side
            st.session_state.current_step = 1
            st.rerun()

def render_department_selection():
    st.header("Selecteer de afdeling")
    
    for dept in st.session_state.BUSINESS_SIDES[st.session_state.business_side].keys():
        if st.button(dept, key=f"department_{dept}"):
            st.session_state.department = dept
            st.session_state.current_step = 2
            st.rerun()

def render_conversation_type_selection():
    st.header("Selecteer het gesprekstype")
    
    conversation_types = st.session_state.BUSINESS_SIDES[st.session_state.business_side][st.session_state.department]
    selected_type = st.selectbox("Gesprekstype", conversation_types)
    
    if st.button("Bevestig gesprekstype"):
        st.session_state.conversation_type = selected_type
        st.session_state.current_step = 3
        st.rerun()

def render_input_method_selection():
    st.header("Selecteer de invoermethode")
    
    for method in st.session_state.INPUT_METHODS:
        if st.button(method, key=f"input_method_{method}"):
            st.session_state.input_method = method
            st.session_state.current_step = 4
            st.rerun()

def render_prompt_selection():
    st.header("Selecteer de prompt")
    
    if not st.session_state.department:
        st.warning("Selecteer eerst een afdeling.")
        return
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        for prompt in st.session_state.DEPARTMENTS[st.session_state.department]:
            if st.button(prompt, key=f"prompt_button_{prompt}", use_container_width=True):
                st.session_state.prompt = prompt
                st.session_state.current_step = 3  # Move to next step
                st.rerun()

def render_summary():
    colored_header("Samenvatting", description="Bekijk en bewerk de gegenereerde samenvatting")
    
    if st.session_state.input_method == "Voer tekst in of plak tekst":
        st.session_state.input_text = display_text_input("Voer tekst in:", value=st.session_state.input_text, height=200)
        if st.button("Samenvatten"):
            with st.spinner("Samenvatting maken..."):
                result = run_summarization(st.session_state.input_text, st.session_state.conversation_type, st.session_state.user_name)
                handle_summarization_result(result, st.session_state.input_text)

    elif st.session_state.input_method in ["Upload audio", "Neem audio op"]:
        handle_audio_input()

    elif st.session_state.input_method == "Upload tekst":
        uploaded_file = display_file_uploader("Kies een bestand", type=['txt', 'docx', 'pdf'])
        if uploaded_file:
            with st.spinner("Samenvatting maken..."):
                st.session_state.transcript = process_uploaded_file(uploaded_file)
                result = run_summarization(st.session_state.transcript, st.session_state.conversation_type, st.session_state.user_name)
                handle_summarization_result(result, st.session_state.transcript)

    if st.session_state.get('summary'):
        st.markdown("### Gegenereerde samenvatting:")
        st.markdown(st.session_state.summary)
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Download als Word"):
                doc = create_word_document(st.session_state.summary)
                st.download_button(
                    label="Download Word bestand",
                    data=doc,
                    file_name="samenvatting.docx",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                )
        with col2:
            st_copy_to_clipboard(st.session_state.summary, "Kopieer naar klembord")

def handle_summarization_result(result, input_text):
    if result["error"] is None:
        st.session_state.summary = result["summary"]
        update_gesprekslog(input_text, result["summary"])
        st.success("Samenvatting voltooid!")
    else:
        st.error(f"Er is een fout opgetreden: {result['error']}")
    
    if st.button("Probeer opnieuw"):
        st.rerun()

def process_text_input():
    with st.spinner("Samenvatting maken..."):
        result = run_summarization(st.session_state.input_text, st.session_state.prompt, st.session_state.user_name)
        handle_summarization_result(result, st.session_state.input_text)

def handle_audio_input():
    try:
        result = utils_process_audio_input(st.session_state.input_method, st.session_state.prompt, st.session_state.user_name)
        if result:
            handle_summarization_result(result, result.get("transcript", ""))
    except Exception as e:
        st.error(f"Er is een fout opgetreden bij het verwerken van de audio: {str(e)}")
        if st.button("Probeer opnieuw"):
            st.rerun()

def process_file_input(uploaded_file):
    st.session_state.transcript = process_uploaded_file(uploaded_file)
    with st.spinner("Samenvatting maken..."):
        result = run_summarization(st.session_state.transcript, st.session_state.prompt, st.session_state.user_name)
        handle_summarization_result(result, st.session_state.transcript)

def render_feedback_form():
    st.subheader("Geef feedback")
    
    with st.form(key="feedback_form"):
        user_first_name = st.text_input("Uw voornaam (verplicht bij feedback):")
        feedback = st.radio("Was dit antwoord nuttig?", ["Positief", "Negatief"])
        additional_feedback = st.text_area("Laat aanvullende feedback achter:")
        submit_button = st.form_submit_button(label="Verzenden")

        if submit_button:
            if not user_first_name:
                st.warning("Voornaam is verplicht bij het geven van feedback.")
            else:
                success = send_feedback_email(
                    transcript=st.session_state.get('transcript', ''),
                    summary=st.session_state.get('summary', ''),
                    feedback=feedback,
                    additional_feedback=additional_feedback,
                    user_first_name=user_first_name
                )
                if success:
                    st.success("Bedankt voor uw feedback!")
                else:
                    st.error("Er is een fout opgetreden bij het verzenden van de feedback. Probeer het later opnieuw.")

def render_conversation_history():
    st.subheader("Laatste vijf gesprekken")
    for i, gesprek in enumerate(st.session_state.get('gesprekslog', [])[:5]):
        with st.expander(f"Gesprek {i+1} op {gesprek['time']}"):
            st.markdown("**Transcript:**")
            display_transcript(gesprek["transcript"])
            st.markdown("**Samenvatting:**")
            st.markdown(gesprek["summary"])

def validate_step(step):
    if step == 0 and 'business_side' not in st.session_state:
        return False
    elif step == 1 and 'department' not in st.session_state:
        return False
    elif step == 2 and 'conversation_type' not in st.session_state:
        return False
    elif step == 3 and 'input_method' not in st.session_state:
        return False
    return True