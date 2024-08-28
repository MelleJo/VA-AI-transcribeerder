import streamlit as st
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from utils.text_processing import load_prompt, get_local_time
import logging

logger = logging.getLogger(__name__)

def get_prompt(prompt_name):
    prompt_file = f"{prompt_name.lower().replace(' ', '_')}.txt"
    return load_prompt(prompt_file)

def summarize_text(text, prompt_name, user_name):
    logger.debug(f"Starting summarize_text for prompt: {prompt_name}")
    logger.debug(f"Input text length: {len(text)}")
    
    prompt = get_prompt(prompt_name)
    current_time = get_local_time()
    
    full_prompt = f"""
    {prompt_name}
    {current_time}
    {user_name}
    Gesproken met: [invullen achteraf]

    {prompt}

    Actiepunten/deadlines/afspraken:
    - [Actiepunt 1] - [Verantwoordelijke/Deadline]
    - [Actiepunt 2] - [Verantwoordelijke/Deadline]
    - ...

    Originele tekst:
    {text}
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
        raise e

def run_summarization(text, prompt_name):
    try:
        user_name = st.session_state.get('user_name', '[gebruiker_naam]')
        summary = summarize_text(text, prompt_name, user_name)
        return {"summary": summary, "error": None}
    except Exception as e:
        return {"summary": None, "error": str(e)}