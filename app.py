import streamlit as st
from langchain_openai import ChatOpenAI
from langchain.chains import MapReduceDocumentsChain, ReduceDocumentsChain, LLMChain, StuffDocumentsChain
from langchain.prompts import ChatPromptTemplate, PromptTemplate
from langchain.text_splitter import CharacterTextSplitter
from langchain.output_parsers import StrOutputParser
import os
import re
import time

def load_prompt(department):
    if department == "Financiële Planning":
        file_name = "financiele planning"
    else:
        file_name = department.replace(' ', '_').lower()
    prompt_file_path = f'prompts/{file_name}'
    try:
        with open(prompt_file_path, 'r', encoding='utf-8') as file:
            return file.read()
    except FileNotFoundError:
        st.error(f"Promptbestand voor '{department}' niet gevonden. Verwacht bestandspad: {prompt_file_path}")
        return None

# Define the function for generating response using MapReduce logic
def generate_response_with_map_reduce(text, openai_api_key):
    # Initialize the LLM with OpenAI Chat
    llm = ChatOpenAI(api_key=openai_api_key, model_name="gpt-4")

    # Define Map Chain
    map_template = """The following is a document: {doc} Please summarize this document."""
    map_prompt = PromptTemplate.from_template(map_template)
    map_chain = LLMChain(llm=llm, prompt=map_prompt)

    # Define Reduce Chain
    reduce_template = """The following is a set of summaries: {docs} Take these and distill it into a final, consolidated summary of the main themes."""
    reduce_prompt = PromptTemplate.from_template(reduce_template)
    reduce_chain = LLMChain(llm=llm, prompt=reduce_prompt)
    combine_documents_chain = StuffDocumentsChain(llm_chain=reduce_chain, document_variable_name="docs")

    reduce_documents_chain = ReduceDocumentsChain(
        combine_documents_chain=combine_documents_chain,
        collapse_documents_chain=combine_documents_chain,
        token_max=4000,
    )

    # Combining documents by mapping a chain over them, then combining results
    map_reduce_chain = MapReduceDocumentsChain(
        llm_chain=map_chain,
        reduce_documents_chain=reduce_documents_chain,
        document_variable_name="doc",
        return_intermediate_steps=False,
    )

    # Split text into chunks
    text_splitter = CharacterTextSplitter(chunk_size=1000, chunk_overlap=0)
    split_docs = text_splitter.split(text)

    # Run Map-Reduce Chain
    final_summary = map_reduce_chain.run(split_docs)
    return final_summary

def app_ui():
    st.title("VA Gesprekssamenvatter")
    department = st.selectbox("Kies uw afdeling:", ["Schadebehandelaar", "Particulieren", "Bedrijven", "Financiële Planning"])
    user_input = st.text_area("Plak hier uw tekst:", height=250)

    if st.button("Genereer Samenvatting"):
        direct_text = user_input
        if direct_text:
            prompt = load_prompt(department)
            if prompt is not None:
                summary = generate_response_with_map_reduce(direct_text, st.secrets["openai"]["api_key"])
                st.subheader("Samenvatting")
                st.write(summary)
            else:
                st.error("Kon geen samenvatting genereren. Controleer de geselecteerde afdeling.")
        else:
            st.error("Voer alstublieft wat tekst in of upload een MP3-bestand.")

app_ui()
