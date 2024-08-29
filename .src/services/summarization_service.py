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

def get_prompt(conversation_type):
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'prompts'))
    business_side = st.session_state.get('business_side')
    department = st.session_state.get('department')
    
    possible_paths = [
        os.path.join(base_dir, business_side.lower(), department.lower(), f"{conversation_type.lower().replace(' ', '_')}.txt"),
        os.path.join(base_dir, department.lower(), f"{conversation_type.lower().replace(' ', '_')}.txt"),
        os.path.join(base_dir, f"{conversation_type.lower().replace(' ', '_')}.txt"),
    ]
    
    for path in possible_paths:
        logger.debug(f"Attempting to load prompt from: {path}")
        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8') as file:
                return file.read()
    
    logger.error(f"No prompt file found for conversation type: {conversation_type}")
    raise FileNotFoundError(f"No prompt file found for conversation type: {conversation_type}")

def summarize_text(text, department, prompt_name, user_name):
    logger.debug(f"Starting summarize_text for department: {department}, prompt: {prompt_name}")
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
        model="gpt-4o-2024-08-06",
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