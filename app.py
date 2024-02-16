import streamlit as st
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
import os

# Initialisatie van sessie status
if 'page' not in st.session_state:
    st.session_state['page'] = 1
if 'sub_department' not in st.session_state:
    st.session_state['sub_department'] = None

def load_prompt(department):
    prompt_file_path = f'prompts/{department.lower()}.txt'
    try:
        with open(prompt_file_path, 'r', encoding='utf-8') as file:
            prompt_text = file.read()
            return prompt_text
    except FileNotFoundError:
        return ""

def split_text(text, max_length=2000):
    if len(text) <= max_length:
        return [text]
    segments = []
    while text:
        segment = text[:max_length]
        last_space = segment.rfind(' ')
        if last_space != -1 and len(text) > max_length:
            segments.append(text[:last_space])
            text = text[last_space+1:]
        else:
            segments.append(text)
            break
    return segments

def generate_response(segment, department, openai_api_key):
    department_prompt = load_prompt(department)
    full_prompt = f"{department_prompt}\n\n{segment}"
    prompt_template = ChatPromptTemplate.from_template(full_prompt)
    model = ChatOpenAI(api_key=openai_api_key, model_name="gpt-4-turbo-preview", temperature=0.20)
    chain = prompt_template | model | StrOutputParser()
    summary = chain.invoke({"transcript": segment})
    return summary

def summarize_text(text, department, openai_api_key):
    segments = split_text(text)
    summaries = []
    for i, segment in enumerate(segments, start=1):
        summary = generate_response(segment, department, openai_api_key)
        summaries.append(summary)
        st.write(f"Chunk {i}/{len(segments)} verwerkt.")
    return " ".join(summaries)

def upload_or_text_page():
    st.title('VA Gesprekssamenvatter')
    uploaded_file = st.file_uploader("Kies een MP3-bestand", type="mp3")
    if uploaded_file is not None:
        temp_dir = "temp"
        os.makedirs(temp_dir, exist_ok=True)
        temp_path = os.path.join(temp_dir, uploaded_file.name)
        with open(temp_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        st.session_state['uploaded_file_path'] = temp_path
        st.session_state['page'] = 1.5  # Ga naar de afdelingsselectie
    elif st.button("Of plak hier uw tekst in plaats van een MP3 te uploaden"):
        st.session_state['page'] = 4

def department_selection_page():
    st.title('Kies uw afdeling')
    department = st.selectbox("Selecteer de afdeling:", ["Schadebehandelaar", "Particulieren", "Bedrijven", "Financiële Planning"])
    st.session_state['department'] = department
    if department == "Financiële Planning":
        st.session_state['sub_department'] = st.selectbox("Selecteer de subafdeling:", ["Pensioen", "Collectief", "Inkomen", "Planning", "Hypotheek"])
    if st.button("Ga door naar samenvatting"):
        st.session_state['page'] = 3

def text_input_page():
    st.title("Tekst voor Samenvatting")
    direct_text = st.text_area("Plak de tekst hier", '', height=300)
    if st.button('Verzend tekst'):
        st.session_state['direct_text'] = direct_text
        st.session_state['page'] = 3

def summary_page():
    st.title("Samenvatting van het Gesprek")
    if 'direct_text' in st.session_state:
        final_summary = summarize_text(
            st.session_state['direct_text'],
            st.session_state['department'],
            st.secrets["openai"]["api_key"]
        )
        st.text_area("Samenvatting", final_summary, height=150)

# Pagina navigatie
if st.session_state['page'] == 1:
    upload_or_text_page()
elif st.session_state['page'] == 4:
    text_input_page()
elif st.session_state['page'] == 1.5:
    department_selection_page()
elif st.session_state['page'] == 3:
    summary_page()
