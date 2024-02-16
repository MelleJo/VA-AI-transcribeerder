import streamlit as st
from speechmatics.models import ConnectionSettings
from speechmatics.batch_client import BatchClient
from httpx import HTTPStatusError
import os
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from langchain_core.output_parsers import StrOutputParser

# Initialisatie van pagina in sessie status
if 'page' not in st.session_state:
    st.session_state['page'] = 1
if 'sub_department' not in st.session_state:
    st.session_state['sub_department'] = None

# Functie om de prompt te laden
def load_prompt(department):
    prompt_file_path = f'prompts/{department.lower()}.txt'
    try:
        with open(prompt_file_path, 'r', encoding='utf-8') as file:
            prompt_text = file.read()
            st.write("Prompt gevonden, jippie!")
            return prompt_text
    except FileNotFoundError:
        st.write("Prompt niet gevonden (fout)")
        return ""

# Functie om de samenvatting te genereren
def generate_response(txt, speaker1, speaker2, subject, department, sub_department, openai_api_key):
    department_prompt = load_prompt(department)
    full_prompt = f"{department_prompt}\n\n### Transcript Informatie:\n" + \
                  f"- **Transcript**: {txt}\n- **Spreker 1**: {speaker1}\n- **Spreker 2**: {speaker2}\n- **Onderwerp**: {subject}\n\n" + \
                  "### Gesprekssamenvatting:\n...\n\n### Actiepunten:\n...\n\n### Einde Samenvatting:"
    
    prompt_template = ChatPromptTemplate.from_template(full_prompt)
    model = ChatOpenAI(api_key=openai_api_key, model_name="gpt-4-turbo-preview", temperature=0.20)
    chain = prompt_template | model | StrOutputParser()
    summary = chain.invoke({"transcript": txt, "speaker1": speaker1, "speaker2": speaker2, "subject": subject})
    return summary

# Pagina voor het selecteren van de afdeling
def department_selection_page():
    st.title('Kies uw afdeling')
    department = st.selectbox("Selecteer de afdeling:", ["Schadebehandelaar", "Particulieren", "Bedrijven", "Financiële Planning"])
    sub_department = None
    # TODO: Add subdepartment selection if department == "Financiële Planning":
        # sub_department = st.selectbox("Selecteer de subafdeling:", ["Pensioen", "Collectief", "Inkomen", "Planning", "Hypotheek"])
    if st.button("Ga door naar samenvatting"):
        st.session_state['department'] = department
        # st.session_state['sub_department'] = sub_department
        st.session_state['page'] = 3

# Pagina voor het uploaden van bestanden en directe tekstinput
def upload_page():
    st.title('VA Gesprekssamenvatter')
    uploaded_file = st.file_uploader("Kies een MP3-bestand", type="mp3")
    if uploaded_file is not None:
        temp_dir = "temp"
        os.makedirs(temp_dir, exist_ok=True)
        temp_path = os.path.join(temp_dir, uploaded_file.name)
        with open(temp_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        st.session_state['uploaded_file_path'] = temp_path
        st.session_state['page'] = 1.5
    if st.button("Of plak hier uw tekst in plaats van een MP3 te uploaden"):
        st.session_state['page'] = 4

# Pagina voor directe tekstinput
def text_input_page():
    st.title("Tekst voor Samenvatting")
    direct_text = st.text_area("Plak de tekst hier", '', height=300)
    if st.button('Verzend tekst'):
        st.session_state['direct_text'] = direct_text
        st.session_state['page'] = 1.5

# Pagina voor samenvatting
def summary_page():
    st.title("Samenvatting van het Gesprek")
    text_to_summarize = st.session_state.get('direct_text', '')
    if text_to_summarize and 'department' in st.session_state:
        summary = generate_response(
            text_to_summarize,
            "Spreker 1",
            "Spreker 2",
            "Onderwerp",
            st.session_state['department'],
            st.session_state['sub_department'],
            st.secrets["openai"]["api_key"]
        )
        st.text_area("Samenvatting", summary, height=150)

# Pagina navigatie
if st.session_state['page'] == 1:
    upload_page()
elif st.session_state['page'] == 4:
    text_input_page()
elif st.session_state['page'] == 1.5:
    department_selection_page()
elif st.session_state['page'] == 3:
    summary_page()
