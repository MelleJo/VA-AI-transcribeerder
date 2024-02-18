import streamlit as st
import os
from langchain_openai import ChatOpenAI
from langchain.chains import MapReduceDocumentsChain, ReduceDocumentsChain, LLMChain, StuffDocumentsChain
from langchain.prompts import PromptTemplate
from langchain.text_splitter import CharacterTextSplitter, Document

# Define the mapping of departments to their respective prompt filenames
DEPARTMENT_PROMPT_MAPPING = {
    "Schadebehandelaar": "schadebehandelaar",
    "Particulieren": "particulieren",
    "Bedrijven": "bedrijven",
    "Financiële Planning": "financiele planning"
}

def load_prompt(department):
    """
    Load the prompt for the selected department from the 'prompts' directory.
    """
    base_dir = 'prompts'  # Assuming the 'prompts' directory is at the root level of your project
    file_name = DEPARTMENT_PROMPT_MAPPING.get(department, "").replace(' ', '_').lower()
    prompt_file_path = os.path.join(base_dir, file_name)

    try:
        with open(prompt_file_path, 'r', encoding='utf-8') as file:
            return file.read()
    except FileNotFoundError:
        st.error(f"Promptbestand voor '{department}' niet gevonden. Verwacht bestandspad: {prompt_file_path}")
        return ""
    except Exception as e:
        st.error(f"Een fout is opgetreden bij het laden van het promptbestand: {e}")
        return ""

def split_text(text):
    """
    Split the text into manageable chunks.
    """
    text_splitter = CharacterTextSplitter(separator="\n\n", chunk_size=1000, chunk_overlap=200, length_function=len, is_separator_regex=False)
    return text_splitter.create_documents([text])

def generate_response_with_map_reduce(text, openai_api_key):
    """
    Generate a summary using Map-Reduce logic with correct input handling.
    """
    llm = ChatOpenAI(api_key=openai_api_key, model_name="gpt-4")
    map_template = "Please summarize this document: {doc}"
    map_prompt = PromptTemplate.from_template(map_template)
    map_chain = LLMChain(llm=llm, prompt=map_prompt)

    reduce_template = "Take these summaries and distill them into a final, consolidated summary: {docs}"
    reduce_prompt = PromptTemplate.from_template(reduce_template)
    reduce_chain = LLMChain(llm=llm, prompt=reduce_prompt)
    combine_documents_chain = StuffDocumentsChain(llm_chain=reduce_chain, document_variable_name="docs")

    reduce_documents_chain = ReduceDocumentsChain(
        combine_documents_chain=combine_documents_chain,
        collapse_documents_chain=combine_documents_chain,
        token_max=4000,
    )

    map_reduce_chain = MapReduceDocumentsChain(
        llm_chain=map_chain,
        reduce_documents_chain=reduce_documents_chain,
        document_variable_name="doc",
        return_intermediate_steps=False,
    )

    split_docs = split_text(text)
    if split_docs:
        final_summary = map_reduce_chain.invoke(split_docs)  # Adjust this line as per the expected input format
        return final_summary

def app_ui():
    """
    Streamlit App UI for generating summaries based on department-specific prompts.
    """
    st.title("VA Gesprekssamenvatter")
    department = st.selectbox("Kies uw afdeling:", list(DEPARTMENT_PROMPT_MAPPING.keys()))
    user_input = st.text_area("Plak hier uw tekst:", height=250)

    if st.button("Genereer Samenvatting"):
        direct_text = user_input
        if direct_text:
            prompt = load_prompt(department)
            if prompt:
                # Assuming you will use `prompt` in your processing logic
                summary = generate_response_with_map_reduce(direct_text, st.secrets["openai"]["api_key"])
                st.subheader("Samenvatting")
                st.write(summary)
            else:
                st.error("Kon geen samenvatting genereren. Controleer de geselecteerde afdeling.")
        else:
            st.error("Voer alstublieft wat tekst in.")

app_ui()
