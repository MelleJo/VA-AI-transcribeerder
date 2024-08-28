import streamlit as st
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from utils.text_processing import load_prompt, get_local_time
import logging
import os

logger = logging.getLogger(__name__)

def get_prompt(department, prompt_name):
    # Normalize the department and prompt name
    normalized_department = department.lower().replace(' ', '_')
    normalized_prompt_name = prompt_name.lower().replace(' ', '_')
    
    # Construct the path based on the provided directory structure
    prompt_file = os.path.join(st.session_state.PROMPTS_DIR, normalized_department, f"{normalized_prompt_name}.txt")
    
    # Check if the file exists in the constructed path
    if not os.path.exists(prompt_file):
        raise FileNotFoundError(f"Bestand niet gevonden: {prompt_file}")
    
    return load_prompt(prompt_file)

def summarize_text(text, department, prompt_name, user_name):
    logger.debug(f"Starting summarize_text for prompt: {prompt_name}")
    logger.debug(f"Input text length: {len(text)}")
    
    prompt = get_prompt(department, prompt_name)
    current_time = get_local_time()
    
    full_prompt = f"""
    {prompt_name}
    {current_time}
    {user_name}
    Gesproken met: [invullen achteraf]

    {prompt}

    Originele tekst:
    {text}
    """
    
    logger.debug(f"Full prompt length: {len(full_prompt)}")
    chat_model = ChatOpenAI(api_key=st.secrets["OPENAI_API_KEY"], model="gpt-4", temperature=0)
    
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