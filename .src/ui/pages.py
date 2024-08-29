import streamlit as st
from streamlit_antd.tabs import st_antd_tabs
from streamlit_antd.cascader import st_antd_cascader
from streamlit_antd.result import Action, st_antd_result
from streamlit_antd.breadcrumb import st_antd_breadcrumb
from streamlit_antd.cards import Action as CardAction, Item, st_antd_cards
#from streamlit_antd.select import st_antd_select
from streamlit_antd.button import st_antd_button

from ui.components.fancy_select import fancy_select
from ui.components import display_transcript, display_summary, display_text_input, display_file_uploader
from services.email_service import send_feedback_email
from services.summarization_service import run_summarization
from utils.audio_processing import process_audio_input
from utils.file_processing import process_uploaded_file
from utils.text_processing import update_gesprekslog


def render_wizard():
    st.title("Gesprekssamenvatter")

    steps = ["Bedrijfsonderdeel", "Afdeling", "Prompt", "Invoermethode", "Samenvatting"]
    current_step = st.session_state.current_step
    
    if current_step == 0:
        render_business_side_selection()
    elif current_step == 1:
        render_department_selection()
    elif current_step == 2:
        render_prompt_selection()
    elif current_step == 3:
        render_input_method_selection()
    elif current_step == 4:
        render_summary()

def render_business_side_selection():
    st.header("Selecteer het bedrijfsonderdeel")
    
    user_name = st.text_input("Uw naam (optioneel):", value=st.session_state.user_name, key="user_name_input")
    
    if user_name != st.session_state.user_name:
        st.session_state.user_name = user_name

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        for side in st.session_state.BUSINESS_SIDES:
            if st.button(
                side,
                key=f"business_side_button_{side}",
                use_container_width=True,
            ):
                st.session_state.business_side = side
                st.session_state.current_step = 1  # Move to next step
                st.rerun()

def render_department_selection():
    st.header("Selecteer de afdeling")
    
    if not st.session_state.business_side:
        st.warning("Selecteer eerst een bedrijfsonderdeel.")
        return
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        for dept in st.session_state.DEPARTMENTS.keys():
            if st.button(dept, key=f"department_button_{dept}", use_container_width=True):
                st.session_state.department = dept
                st.session_state.current_step = 2  # Move to next step
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

def render_input_method_selection():
    st.header("Selecteer de invoermethode")
    
    if not st.session_state.prompt:
        st.warning("Selecteer eerst een prompt.")
        return
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        for method in st.session_state.INPUT_METHODS:
            if st.button(method, key=f"input_method_button_{method}", use_container_width=True):
                st.session_state.input_method = method
                st.session_state.current_step = 4  # Move to summary step
                st.rerun()

def render_summary():
    st.header("Samenvatting")
    
    if st.session_state.input_method == "Voer tekst in of plak tekst":
        st.session_state.input_text = display_text_input("Voer tekst in:", value=st.session_state.input_text, height=200)
        if st.button("Samenvatten"):
            with st.spinner("Samenvatting maken..."):
                result = run_summarization(st.session_state.input_text, st.session_state.prompt, st.session_state.user_name)
                if result["error"] is None:
                    st.session_state.summary = result["summary"]
                    update_gesprekslog(st.session_state.input_text, result["summary"])
                    st_antd_result(
                        "Samenvatting voltooid!",
                        "De samenvatting is succesvol gegenereerd.",
                        [Action("show", "Toon samenvatting", primary=True)]
                    )
                else:
                    st_antd_result(
                        "Er is een fout opgetreden",
                        result["error"],
                        [Action("retry", "Probeer opnieuw")]
                    )
    elif st.session_state.input_method in ["Upload audio", "Neem audio op"]:
        result = process_audio_input(st.session_state.input_method, st.session_state.prompt, st.session_state.user_name)
        if result and result["error"] is None:
            st.session_state.summary = result["summary"]
            st_antd_result(
                "Samenvatting voltooid!",
                "De samenvatting is succesvol gegenereerd.",
                [Action("show", "Toon samenvatting", primary=True)]
            )
        elif result:
            st_antd_result(
                "Er is een fout opgetreden",
                result["error"],
                [Action("retry", "Probeer opnieuw")]
            )
    elif st.session_state.input_method == "Upload tekst":
        uploaded_file = display_file_uploader("Kies een bestand", type=['txt', 'docx', 'pdf'])
        if uploaded_file:
            st.session_state.transcript = process_uploaded_file(uploaded_file)
            with st.spinner("Samenvatting maken..."):
                result = run_summarization(st.session_state.transcript, st.session_state.prompt, st.session_state.user_name)
                if result["error"] is None:
                    st.session_state.summary = result["summary"]
                    update_gesprekslog(st.session_state.transcript, result["summary"])
                    st_antd_result(
                        "Samenvatting voltooid!",
                        "De samenvatting is succesvol gegenereerd.",
                        [Action("show", "Toon samenvatting", primary=True)]
                    )
                else:
                    st_antd_result(
                        "Er is een fout opgetreden",
                        result["error"],
                        [Action("retry", "Probeer opnieuw")]
                    )

    if st.session_state.summary:
        display_summary(st.session_state.summary)

def render_feedback_form():
    with st.expander("Geef feedback"):
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
    for i, gesprek in enumerate(st.session_state.get('gesprekslog', [])):
        with st.expander(f"Gesprek {i+1} op {gesprek['time']}"):
            st.markdown("**Transcript:**")
            display_transcript(gesprek["transcript"])
            st.markdown("**Samenvatting:**")
            display_summary(gesprek["summary"])
