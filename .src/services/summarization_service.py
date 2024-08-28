import streamlit as st
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from utils.text_processing import load_prompt, get_local_time
import logging

logger = logging.getLogger(__name__)

def get_prompt(prompt_name):
    prompt_file = f"{prompt_name.lower().replace(' ', '_')}.txt"
    return load_prompt(prompt_file)

def summarize_text(text, prompt_name):
    logger.debug(f"Starting summarize_text for prompt: {prompt_name}")
    logger.debug(f"Input text length: {len(text)}")
    
    prompt = get_prompt(prompt_name)
    logger.debug(f"Prompt length: {len(prompt)}")
    chat_model = ChatOpenAI(api_key=st.secrets["OPENAI_API_KEY"], model="gpt-4o", temperature=0)
    
    try:
        prompt_template = ChatPromptTemplate.from_template(prompt)
        chain = prompt_template | chat_model
        logger.debug("Invoking chat model")
        summary = chain.invoke({"text": text}).content
        logger.debug(f"Summary generated. Length: {len(summary)}")
        return summary
    except Exception as e:
        logger.error(f"Error in summarization: {str(e)}")
        if "maximum context length" in str(e):
            logger.warning("Maximum context length exceeded. Attempting chunking.")
            chunk_size = 100000  # Adjust as needed
            chunks = [text[i:i+chunk_size] for i in range(0, len(text), chunk_size)]
            logger.debug(f"Text split into {len(chunks)} chunks")
            summaries = []
            
            for i, chunk in enumerate(chunks):
                logger.debug(f"Processing chunk {i+1} of {len(chunks)}")
                prompt_template = ChatPromptTemplate.from_template(prompt)
                chain = prompt_template | chat_model
                chunk_summary = chain.invoke({"text": chunk}).content
                summaries.append(chunk_summary)
                logger.debug(f"Chunk {i+1} summary length: {len(chunk_summary)}")
            
            final_prompt = "Combine these summaries into a cohesive final summary:\n\n" + "\n\n".join(summaries)
            logger.debug(f"Final prompt length: {len(final_prompt)}")
            final_chain = ChatPromptTemplate.from_template(final_prompt) | chat_model
            final_summary = final_chain.invoke({"text": ""}).content
            logger.debug(f"Final summary length: {len(final_summary)}")
            return final_summary
        else:
            raise e

def run_summarization(text, prompt_name):
    try:
        summary = summarize_text(text, prompt_name)
        return {"summary": summary, "error": None}
    except Exception as e:
        return {"summary": None, "error": str(e)}