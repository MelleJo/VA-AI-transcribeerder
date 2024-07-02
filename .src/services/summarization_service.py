import streamlit as st
from langchain_openai import ChatOpenAI
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from utils.text_processing import load_prompt, get_local_time
import tiktoken
import time

@st.cache_data
def load_department_prompts():
    return {
        "Bedrijven": "veldhuis-advies-groep/bedrijven/MKB/onderhoudsadviesgesprek_tabel_prompt.txt",
        "Financieel Advies": "veldhuis-advies-groep/bedrijven/MKB/onderhoudsadviesgesprek_tabel_prompt.txt",
        "Schadeafdeling": "veldhuis-advies-groep/bedrijven/MKB/onderhoudsadviesgesprek_tabel_prompt.txt",
        "Algemeen": "algemeen/notulen/algemeen_notulen.txt",
        "Arbo": "arbo/algemeen_arbo.txt",
        "Ondersteuning Bedrijfsarts": "arbo/ondersteuning_bedrijfsarts/samenvatting_gesprek_bedrijfsarts.txt",
        "Onderhoudsadviesgesprek in tabelvorm": "veldhuis-advies-groep/bedrijven/MKB/onderhoudsadviesgesprek_tabel_prompt.txt",
        "Notulen van een vergadering": "algemeen/notulen/algemeen_notulen.txt",
        "Verslag van een telefoongesprek": "algemeen/telefoon/algemeen_telefoon.txt",
        "test-prompt (alleen voor Melle!)": "util/test_prompt.txt"
    }

@st.cache_data
def get_combined_prompt(department):
    department_prompts = load_department_prompts()
    prompt_file = department_prompts.get(department, f"{department.lower().replace(' ', '_')}_prompt.txt")
    department_prompt = load_prompt(prompt_file)
    basic_prompt = load_prompt("util/basic_prompt.txt")
    current_time = get_local_time()
    return f"{department_prompt}\n\n{basic_prompt.format(current_time=current_time)}\n\n{{text}}"

def num_tokens_from_string(string: str, model_name: str = "gpt-4o") -> int:
    encoding = tiktoken.encoding_for_model(model_name)
    return len(encoding.encode(string))

def truncate_text_to_token_limit(text: str, limit: int, model_name: str = "gpt-4o") -> str:
    encoding = tiktoken.encoding_for_model(model_name)
    encoded = encoding.encode(text)
    return encoding.decode(encoded[:limit])

def summarize_text(text, department):
    start_time = time.time()
    timing_info = {"prompt_preparation": 0, "model_initialization": 0, "chain_creation": 0, "summarization": 0, "total_time": 0}
    summary = None
    
    try:
        prompt_start = time.time()
        combined_prompt = get_combined_prompt(department)
        timing_info["prompt_preparation"] = time.time() - prompt_start

        model_start = time.time()
        chat_model = ChatOpenAI(api_key=st.secrets["OPENAI_API_KEY"], model="gpt-4o", temperature=0)
        timing_info["model_initialization"] = time.time() - model_start

        chain_start = time.time()
        prompt_template = ChatPromptTemplate.from_template(combined_prompt)
        llm_chain = prompt_template | chat_model | StrOutputParser()
        timing_info["chain_creation"] = time.time() - chain_start

        invoke_start = time.time()
        summary = llm_chain.invoke({"text": text})
        timing_info["summarization"] = time.time() - invoke_start

    except Exception as e:
        st.error(f"Error in summarization: {str(e)}")
    
    finally:
        timing_info["total_time"] = time.time() - start_time
        return summary, timing_info

def fallback_summarization(text, prompt, chat_model, start_time):
    timing_info = {"prompt_preparation": 0, "model_initialization": 0, "chain_creation": 0, "summarization": 0}
    
    try:
        prompt_tokens = num_tokens_from_string(prompt, "gpt-4o")
        text_tokens = num_tokens_from_string(text, "gpt-4o")
        total_tokens = prompt_tokens + text_tokens

        if total_tokens <= 120000:
            invoke_start = time.time()
            prompt_template = ChatPromptTemplate.from_template(prompt)
            llm_chain = prompt_template | chat_model | StrOutputParser()
            summary = llm_chain.invoke({"text": text})
            timing_info["summarization"] = time.time() - invoke_start
        else:
            st.warning("Text is too long. Using two-pass summarization.")
            summary = two_pass_summarization(text, prompt, chat_model, prompt_tokens)
            timing_info["summarization"] = time.time() - start_time

        timing_info["total_time"] = time.time() - start_time
        return summary, timing_info

    except Exception as e:
        st.error(f"Error in fallback summarization: {str(e)}")
        return None, {"error": str(e), "total_time": time.time() - start_time}

def two_pass_summarization(text, prompt, chat_model, prompt_tokens):
    first_chunk_tokens = 120000 - prompt_tokens - 1000
    first_chunk = truncate_text_to_token_limit(text, first_chunk_tokens)
    
    first_prompt = ChatPromptTemplate.from_template(f"{prompt}\n\n{{text}}")
    first_chain = first_prompt | chat_model | StrOutputParser()
    first_summary = first_chain.invoke({"text": first_chunk})
    
    remaining_text = text[len(first_chunk):]
    if remaining_text:
        second_prompt = ChatPromptTemplate.from_template(
            f"{prompt}\n\nThis is a continuation of a longer text. "
            f"The first part was summarized as follows:\n\n{first_summary}\n\n"
            f"Please summarize the following continuation:\n\n{{text}}"
        )
        second_chain = second_prompt | chat_model | StrOutputParser()
        second_summary = second_chain.invoke({"text": remaining_text})
        
        final_prompt = ChatPromptTemplate.from_template(
            "Combine these two summaries into a cohesive final summary:\n\n"
            "First part: {first_summary}\n\n"
            "Second part: {second_summary}"
        )
        final_chain = final_prompt | chat_model | StrOutputParser()
        final_summary = final_chain.invoke({
            "first_summary": first_summary,
            "second_summary": second_summary
        })
        return final_summary
    else:
        return first_summary
