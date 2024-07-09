import streamlit as st
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from utils.text_processing import load_prompt, get_local_time

def get_combined_prompt(department):
    department_prompts = {
        "Bedrijven": "onderhoudsadviesgesprek_tabel_prompt.txt",
        "Financieel Advies": "onderhoudsadviesgesprek_tabel_prompt.txt",
        "Schadeafdeling": "onderhoudsadviesgesprek_tabel_prompt.txt",
        "Algemeen": "algemeen_notulen.txt",
        "Arbo": "algemeen_arbo.txt",
        "Ondersteuning Bedrijfsarts": "samenvatting_gesprek_bedrijfsarts.txt",
        "Onderhoudsadviesgesprek in tabelvorm": "onderhoudsadviesgesprek_tabel_prompt.txt",
        "Notulen van een vergadering": "algemeen_notulen.txt",
        "Verslag van een telefoongesprek": "algemeen_telefoon.txt",
        "Deelnemersgesprekken collectief pensioen": "deelnemersgesprekken_collectief_pensioen_prompt.txt",
        "test-prompt (alleen voor Melle!)": "util/test_prompt.txt"
    }
    prompt_file = department_prompts.get(department, f"{department.lower().replace(' ', '_')}_prompt.txt")
    department_prompt = load_prompt(prompt_file)
    basic_prompt = load_prompt("util/basic_prompt.txt")
    current_time = get_local_time()
    return f"{department_prompt}\n\n{basic_prompt.format(current_time=current_time)}\n\n{{text}}"

def summarize_text(text, department):
    if department == "Deelnemersgesprekken collectief pensioen":
        return summarize_deelnemersgesprekken(text)
    
    combined_prompt = get_combined_prompt(department)
    chat_model = ChatOpenAI(api_key=st.secrets["OPENAI_API_KEY"], model="gpt-4o", temperature=0)
    
    try:
        prompt_template = ChatPromptTemplate.from_template(combined_prompt)
        chain = prompt_template | chat_model
        return chain.invoke({"text": text}).content
    except Exception as e:
        if "maximum context length" in str(e):
            chunk_size = 100000  # Adjust as needed
            chunks = [text[i:i+chunk_size] for i in range(0, len(text), chunk_size)]
            summaries = []
            
            for chunk in chunks:
                prompt_template = ChatPromptTemplate.from_template(combined_prompt)
                chain = prompt_template | chat_model
                summaries.append(chain.invoke({"text": chunk}).content)
            
            final_prompt = "Combine these summaries into a cohesive final summary:\n\n" + "\n\n".join(summaries)
            final_chain = ChatPromptTemplate.from_template(final_prompt) | chat_model
            return final_chain.invoke({"text": ""}).content
        else:
            raise e

def summarize_deelnemersgesprekken(text):
    prompt = load_prompt("deelnemersgesprekken_collectief_pensioen_prompt.txt")
    chat_model = ChatOpenAI(api_key=st.secrets["OPENAI_API_KEY"], model="gpt-4o", temperature=0)
    
    prompt_template = ChatPromptTemplate.from_template(prompt)
    chain = prompt_template | chat_model
    return chain.invoke({"text": text}).content

def run_summarization(text, department):
    try:
        summary = summarize_text(text, department)
        return {"summary": summary, "error": None}
    except Exception as e:
        return {"summary": None, "error": str(e)}