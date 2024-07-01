import streamlit as st
from langchain_openai import ChatOpenAI
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from utils.text_processing import load_prompt, get_local_time
import tiktoken

def num_tokens_from_string(string: str, model_name: str = "gpt-4o") -> int:
    encoding = tiktoken.encoding_for_model(model_name)
    return len(encoding.encode(string))

def truncate_text_to_token_limit(text: str, limit: int, model_name: str = "gpt-4o") -> str:
    encoding = tiktoken.encoding_for_model(model_name)
    encoded = encoding.encode(text)
    return encoding.decode(encoded[:limit])

def summarize_text(text, department):
    with st.spinner("Samenvatting maken..."):
        department_prompts = {
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
        prompt_file = department_prompts.get(department, f"{department.lower().replace(' ', '_')}_prompt.txt")
        department_prompt = load_prompt(prompt_file)
        basic_prompt = load_prompt("util/basic_prompt.txt")
        current_time = get_local_time()
        combined_prompt = f"{department_prompt}\n\n{basic_prompt.format(current_time=current_time)}\n\n{{text}}"
        
        chat_model = ChatOpenAI(api_key=st.secrets["OPENAI_API_KEY"], model="gpt-4o", temperature=0)
        prompt_template = ChatPromptTemplate.from_template(combined_prompt)
        llm_chain = prompt_template | chat_model | StrOutputParser()
        
        prompt_tokens = num_tokens_from_string(combined_prompt, "gpt-4o")
        text_tokens = num_tokens_from_string(text, "gpt-4o")
        total_tokens = prompt_tokens + text_tokens
        
        if total_tokens > 120000:
            st.warning("Text is too long. Using two-pass summarization.")
            return two_pass_summarization(text, combined_prompt, chat_model, prompt_tokens)
        
        try:
            return llm_chain.invoke({"text": text})
        except Exception as e:
            st.error(f"Error summarizing text: {str(e)}")
            return None

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
        return final_chain.invoke({
            "first_summary": first_summary,
            "second_summary": second_summary
        })
    else:
        return first_summary