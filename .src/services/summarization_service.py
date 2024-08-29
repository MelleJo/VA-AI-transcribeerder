import streamlit as st
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from utils.text_processing import load_prompt, get_local_time
import logging
import os
import functools
from langchain.callbacks.streaming_stdout import StreamingStdOutCallbackHandler

logger = logging.getLogger(__name__)

def get_all_prompts():
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'prompts'))
    prompts = []
    for root, dirs, files in os.walk(base_dir):
        for file in files:
            if file.endswith('.txt'):
                relative_path = os.path.relpath(os.path.join(root, file), base_dir)
                prompts.append(relative_path)
    return prompts

import os
from config import load_config

# Load configurations from config.py
config = load_config()

def get_prompt(department, prompt_name):
    # Construct the path based on the prompt name directly
    normalized_prompt_name = prompt_name.lower().replace(' ', '_')
    
    # Use the PROMPTS_DIR and build the full path to the prompt file
    prompt_file = os.path.join(config['PROMPTS_DIR'], f"{normalized_prompt_name}.txt")
    
    # Debugging line to check what path is being constructed
    st.write(f"Looking for prompt file at: {prompt_file}")
    
    # Ensure the constructed path points to a valid file
    if not os.path.exists(prompt_file) or not os.path.isfile(prompt_file):
        raise FileNotFoundError(f"Bestand niet gevonden: {prompt_file}")
    
    # Load and return the prompt content
    return load_prompt(prompt_file)




def summarize_text(text, conversation_type, user_name):
    logger.debug(f"Starting summarize_text for conversation type: {conversation_type}")
    logger.debug(f"Input text length: {len(text)}")
    
    try:
        prompt = get_prompt(conversation_type)
    except FileNotFoundError as e:
        logger.error(f"Prompt file not found: {str(e)}")
        return f"Error: {str(e)}"

    current_time = get_local_time()
    
    full_prompt = f"""
    {conversation_type}
    {current_time}
    {user_name}
    Betreft: [invullen achteraf]

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

    Eindig je samenvatting met de tekst 'EINDE_SAMENVATTING'.
    """
    
    logger.debug(f"Full prompt length: {len(full_prompt)}")
    chat_model = ChatOpenAI(
        api_key=st.secrets["OPENAI_API_KEY"],
        model="gpt-4-1106-preview",
        temperature=0,
        streaming=True,
        callbacks=[StreamingStdOutCallbackHandler()]
    )
    
    try:
        prompt_template = ChatPromptTemplate.from_template(full_prompt)
        chain = prompt_template | chat_model
        logger.debug("Invoking chat model")
        summary = ""
        for chunk in chain.stream({"text": text}):
            summary += chunk.content
            if "EINDE_SAMENVATTING" in summary:
                summary = summary.replace("EINDE_SAMENVATTING", "").strip()
                break
        logger.debug(f"Summary generated. Length: {len(summary)}")
        return summary
    except Exception as e:
        logger.error(f"Error in summarization: {str(e)}")
        return f"Error in summarization: {str(e)}"

def run_summarization(text, conversation_type, user_name):
    try:
        logger.debug(f"Running summarization for conversation type: {conversation_type}")
        summary = summarize_text(text, conversation_type, user_name)
        if summary.startswith("Error:"):
            return {"summary": None, "error": summary}
        return {"summary": summary, "error": None}
    except Exception as e:
        logger.error(f"Error in run_summarization: {str(e)}")
        return {"summary": None, "error": str(e)}