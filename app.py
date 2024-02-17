import streamlit as st
from langchain_openai import ChatOpenAI
from langchain.chains import MapReduceDocumentsChain, ReduceDocumentsChain, LLMChain, StuffDocumentsChain
from langchain.prompts import PromptTemplate
from langchain.text_splitter import CharacterTextSplitter, Document

# Load the prompt for the selected department
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
        return ""

# Split the text into manageable chunks
def split_text(text):
    text_splitter = CharacterTextSplitter(
        separator="\n\n", 
        chunk_size=1000, 
        chunk_overlap=200, 
        length_function=len, 
        is_separator_regex=False
    )
    return text_splitter.create_documents([text])

# Generate a summary using Map-Reduce logic
def generate_response_with_map_reduce(text, openai_api_key):
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
        # Correctly access the content of each Document object
        split_docs_flattened = [doc.content for doc in split_docs]  # Use dot notation here
        final_summary = map_reduce_chain.run(split_docs_flattened)
        return final_summary

# Streamlit App UI
def app_ui():
    st.title("VA Gesprekssamenvatter")
    department = st.selectbox("Kies uw afdeling:", ["Schadebehandelaar", "Particulieren", "Bedrijven", "Financiële Planning"])
    user_input = st.text_area("Plak hier uw tekst:", height=250)

    if st.button("Genereer Samenvatting"):
        direct_text = user_input
        if direct_text:
            prompt = load_prompt(department)
            if prompt:
                summary = generate_response_with_map_reduce(direct_text, st.secrets["openai"]["api_key"])
                st.subheader("Samenvatting")
                st.write(summary)
            else:
                st.error("Kon geen samenvatting genereren. Controleer de geselecteerde afdeling.")
        else:
            st.error("Voer alstublieft wat tekst in of upload een MP3-bestand.")

app_ui()
