import streamlit as st
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from utils.text_processing import load_prompt
from datetime import datetime

def run_summarization(text, prompt_name, user_name):
    try:
        prompt = load_prompt(st.session_state.prompt_path)
        summary = summarize_text(text, prompt, prompt_name, user_name)
        return {"summary": summary, "error": None}
    except Exception as e:
        return {"summary": None, "error": str(e)}

def summarize_text(text, prompt, prompt_name, user_name):
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    full_prompt = f"""
    {prompt_name}
    {current_time}
    {user_name}
    Gesproken met: [invullen achteraf]

    {prompt}

    Originele tekst:
    {text}
    """
    
    chat_model = ChatOpenAI(
        api_key=st.secrets["OPENAI_API_KEY"],
        model=st.session_state.config.get('OPENAI_MODEL', 'gpt-4'),
        temperature=st.session_state.config.get('OPENAI_TEMPERATURE', 0)
    )
    
    prompt_template = ChatPromptTemplate.from_template(full_prompt)
    chain = prompt_template | chat_model
    summary = chain.invoke({"text": text}).content
    
    return summary