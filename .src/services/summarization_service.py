import streamlit as st
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from utils.text_processing import load_prompt, get_local_time
import logging
import os

logger = logging.getLogger(__name__)

def get_prompt(department, prompt_name):
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'prompts'))
    possible_filenames = [
        os.path.join(base_dir, department.lower(), f"{prompt_name.lower().replace(' ', '_')}.txt"),
        os.path.join(base_dir, f"{department.lower()}_{prompt_name.lower().replace(' ', '_')}.txt"),
        os.path.join(base_dir, f"{prompt_name.lower().replace(' ', '_')}.txt"),
    ]
    
    for filename in possible_filenames:
        if os.path.exists(filename):
            with open(filename, 'r', encoding='utf-8') as file:
                return file.read()
    
    # If no file is found, raise an error
    raise FileNotFoundError(f"No prompt file found for department '{department}' and prompt '{prompt_name}'. Looked in: {', '.join(possible_filenames)}")

def summarize_text(text, department, prompt_name, user_name):
    logger.debug(f"Starting summarize_text for prompt: {prompt_name}")
    logger.debug(f"Input text length: {len(text)}")
    
    try:
        prompt = get_prompt(department, prompt_name)
    except FileNotFoundError as e:
        logger.error(f"Prompt file not found: {str(e)}")
        return f"Error: {str(e)}"
    
    current_time = get_local_time()
    
    full_prompt = f"""
    {prompt_name}
    {current_time}
    {user_name}
    Gesproken met: [invullen achteraf]

    {prompt}

    Originele tekst:
    {text}

    Zorg ervoor dat je samenvatting de volgende structuur heeft:
    1. Titel
    2. Datum en tijd
    3. Gebruiker
    4. Gesproken met
    5. Hoofdinhoud (meerdere paragrafen indien nodig)
    6. Actiepunten/deadlines/afspraken
    """
    
    logger.debug(f"Full prompt length: {len(full_prompt)}")
    chat_model = ChatOpenAI(api_key=st.secrets["OPENAI_API_KEY"], model="gpt-4o", temperature=0)
    
    try:
        prompt_template = ChatPromptTemplate.from_template(full_prompt)
        chain = prompt_template | chat_model
        logger.debug("Invoking chat model")
        summary = chain.invoke({"text": text}).content
        logger.debug(f"Summary generated. Length: {len(summary)}")
        return summary
    except Exception as e:
        logger.error(f"Error in summarization: {str(e)}")
        return f"Error in summarization: {str(e)}"

def run_summarization(text, prompt_name, user_name):
    try:
        department = st.session_state.department
        summary = summarize_text(text, department, prompt_name, user_name)
        if summary.startswith("Error:"):
            return {"summary": None, "error": summary}
        return {"summary": summary, "error": None}
    except Exception as e:
        return {"summary": None, "error": str(e)}