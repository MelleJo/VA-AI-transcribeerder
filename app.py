import streamlit as st
from langchain_openai import ChatOpenAI
from langchain.chains import LLMChain, MapReduceDocumentsChain, ReduceDocumentsChain, StuffDocumentsChain
from langchain.prompts import PromptTemplate
from langchain.text_splitter import CharacterTextSplitter

# Function to dynamically load the prompt based on department selection
def load_prompt(department):
    # Mapping department to filename
    department_to_filename = {
        "Schadebehandelaar": "schadebehandelaar",
        "Particulieren": "particulieren",
        "Bedrijven": "bedrijven",
        "Financiële Planning": "financiele planning"
    }
    filename = department_to_filename.get(department, "default")
    prompt_file_path = f"prompts/{filename}"

    # Attempt to load the prompt from file
    try:
        with open(prompt_file_path, 'r', encoding='utf-8') as file:
            return file.read()
    except FileNotFoundError:
        st.error(f"Prompt file for '{department}' not found. Expected file path: {prompt_file_path}")
        return None
    except Exception as e:
        st.error(f"An error occurred while loading the prompt: {e}")
        return None

# Function to split text into documents suitable for processing
def split_text(text):
    text_splitter = CharacterTextSplitter(separator="\n\n", chunk_size=1000, chunk_overlap=200, length_function=len)
    return text_splitter.create_documents([text])

# Generate a summary using Map-Reduce logic with LLM
def generate_summary(text, department):
    prompt = load_prompt(department)
    if prompt:
        # Initialize the OpenAI and LLMChain with your API key
        llm = ChatOpenAI(api_key=st.secrets["openai"]["api_key"], model_name="gpt-4")
        map_chain = LLMChain(llm=llm, prompt=PromptTemplate(prompt))

        # Configure reduce chain
        reduce_chain = ReduceDocumentsChain(
            combine_documents_chain=StuffDocumentsChain(llm_chain=map_chain, document_variable_name="docs"),
            token_max=4000,
        )

        # Create MapReduceDocumentsChain
        map_reduce_chain = MapReduceDocumentsChain(
            llm_chain=map_chain,
            reduce_documents_chain=reduce_chain,
            document_variable_name="doc",
            return_intermediate_steps=False,
        )

        split_docs = split_text(text)
        if split_docs:
            final_summary = map_reduce_chain.invoke(split_docs)
            return final_summary
    else:
        return "Prompt loading failed, cannot generate summary."

# UI setup for Streamlit app
st.title("VA Gesprekssamenvatter")
department = st.selectbox("Kies uw afdeling:", ["Schadebehandelaar", "Particulieren", "Bedrijven", "Financiële Planning"])
user_input = st.text_area("Plak hier uw tekst:", height=250)

if st.button("Genereer Samenvatting"):
    summary = generate_summary(user_input, department)
    if summary:
        st.subheader("Samenvatting")
        st.write(summary)
    else:
        st.error("Unable to generate summary. Please check the input and try again.")
