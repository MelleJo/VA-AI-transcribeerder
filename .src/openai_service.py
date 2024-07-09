from langchain_openai import ChatOpenAI
from openai import OpenAI
from langchain.prompts import ChatPromptTemplate
from langchain.chains import LLMChain
import streamlit as st

def get_openai_client():
    if 'openai_client' not in st.session_state:
        st.session_state.openai_client = ChatOpenAI(
            model_name="gpt-4o",
            temperature=0,
            api_key=st.secrets["OPENAI_API_KEY"]
        )
    return st.session_state.openai_client


def perform_gpt4_operation(summary, operation):
    llm = get_openai_client()
    
    prompt = ChatPromptTemplate.from_template(
        "Jij bent een expert in het verwerken van samenvattingen en het uitvoeren van vervolgactie. "
        "Voer de opdracht van de gebruiker uit {operation} met betrekking tot de volgende samenvatting:\n\n{summary}"
    )
    
    chain = LLMChain(llm=llm, prompt=prompt)
    
    response = chain.run(operation=operation, summary=summary)
    return response