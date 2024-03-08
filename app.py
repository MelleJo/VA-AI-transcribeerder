import streamlit as st
import os
import time
import pyperclip
from PyPDF2 import PdfReader
from langchain.text_splitter import CharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain.chains import AnalyzeDocumentChain
from langchain_community.callbacks import get_openai_callback
from langchain.chains.question_answering import load_qa_chain
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from speechmatics.models import ConnectionSettings
from speechmatics.batch_client import BatchClient
from httpx import HTTPStatusError
from openai import OpenAI



# Set your OpenAI and Speechmatics API keys
openai_api_key = st.secrets["openai"]["api_key"]
speechmatics_auth_token = st.secrets["speechmatics"]["auth_token"]

# Define the base directory for the Polisvoorwaardentool
BASE_DIR = os.path.join(os.getcwd(), "preloaded_pdfs", "PolisvoorwaardenVA")

# Define company name mapping
company_name_mapping = {
    "nn": "Nationale Nederlanden",
    "asr": "a.s.r.",
    "nlg": "NLG Verzekeringen",
    "avero": "Avéro Achmea",
    "Avero-p-r521": "Avéro Achmea",
    "europeesche": "Europeesche Verzekeringen",
    "aig": "AIG",
    "allianz": "Allianz",
    "bikerpolis": "Bikerpolis",
    "das": "DAS",
    "guardian": "Guardian",
    "noordeloos": "Noordeloos",
    "reaal": "Reaal",
    "unigarant": "Unigarant",
}

# Function to get all documents from the Polisvoorwaardentool
def get_all_documents():
    all_docs = []
    for root, dirs, files in os.walk(BASE_DIR):
        for file in files:
            if file.endswith('.pdf'):
                path = os.path.join(root, file)
                all_docs.append({'title': file, 'path': path})
    return all_docs

def get_insurance_companies(all_documents):
    companies = set()
    for doc in all_documents:
        parts = doc['title'].split('_')
        if len(parts) >= 2:
            company_key = parts[1].lower()
            company_name = company_name_mapping.get(company_key, company_key.capitalize())
            companies.add(company_name)
    return sorted(companies)

def get_categories():
    try:
        return sorted(next(os.walk(BASE_DIR))[1])
    except StopIteration:
        st.error("Fout bij het openen van categorieën. Controleer of de map bestaat en niet leeg is.")
        return []

def get_documents(category):
    category_path = os.path.join(BASE_DIR, category)
    return sorted([doc for doc in os.listdir(category_path) if doc.endswith('.pdf')])

def extract_text_from_pdf_by_page(file_path):
    pages_text = []
    with open(file_path, 'rb') as file:
        reader = PdfReader(file)
        for page in reader.pages:
            text = page.extract_text()
            if text:
                pages_text.append(text)
    return pages_text


def process_document(document_path, user_question):
    with st.spinner('Denken...'):
        # Extract text from the document
        document_pages = extract_text_from_pdf_by_page(document_path)
        embeddings = OpenAIEmbeddings()
        knowledge_base = FAISS.from_texts(document_pages, embeddings)
        docs = knowledge_base.similarity_search(user_question)
        document_text = " ".join([doc.page_content for doc in docs])

        template = """
        Je bent een ervaren schadebehandelaar met diepgaande kennis van polisvoorwaarden. Jouw taak is om specifieke vragen over dekkingen, uitsluitingen en voorwaarden betrouwbaar en nauwkeurig te beantwoorden, gebruikmakend van de tekst uit de geladen polisvoorwaardendocumenten. Het is essentieel dat je antwoorden direct uit deze documenten haalt en specifiek citeert waar de informatie te vinden is, inclusief paginanummers of sectienummers indien beschikbaar.

        Wanneer je een vraag tegenkomt waarvoor de informatie in de documenten niet volstaat om een betrouwbaar antwoord te geven, vraag dan om verduidelijking bij de gebruiker. Leg uit wat er gespecificeerd moet worden om een nauwkeurig antwoord te kunnen geven. Voor vragen die eenvoudig en rechtstreeks uit de tekst beantwoord kunnen worden, citeer dan de relevante informatie direct.

        Houd er rekening mee dat als de dekking van een schade afhankelijk is van specifieke voorwaarden, je een duidelijke uitleg moet geven over deze voorwaarden. Je hoeft geen algemene disclaimers te geven die logisch zijn voor een schadebehandelaar, maar het is cruciaal om de voorwaarden voor dekking nauwkeurig weer te geven.

        Bovendien, controleer altijd of er een maximale vergoeding gespecificeerd is voor de gedekte voorwerpen en noem dit expliciet in je antwoord. Het is cruciaal dat deze informatie correct is en niet verward wordt met iets anders. Voorbeeld: Als een klant een iPhone laat vallen op het balkon, onderzoek dan niet alleen of de schade gedekt is, maar ook wat de maximale vergoeding is voor mobiele telefoons onder de polisvoorwaarden en vermeld dit duidelijk.

        Bij het beantwoorden van vragen zoals 'Een klant heeft een iPhone laten vallen op het balkon, is dit gedekt?', zorg ervoor dat je eerst bevestigt of 'Mobiele elektronica' verzekerd is op het polisblad. Vervolgens, identificeer of schade door vallen of stoten gedekt is en specificeer de maximale vergoeding die van toepassing is op dergelijke claims. Citeer de relevante sectie(s) uit de polisvoorwaarden die je antwoord ondersteunen, inclusief de pagina- of sectienummers voor directe referentie. 

        Geef een conclusie aan het eind waar je in alle nauwkeurigheid een zo beknopt mogelijk antwoord geeft op de vraag.

        Gegeven de tekst uit de polisvoorwaarden: '{document_text}', en de vraag van de gebruiker: '{user_question}', hoe zou je deze vraag beantwoorden met inachtneming van de bovenstaande instructies?
        """
        
        prompt = ChatPromptTemplate.from_template(template)

        
        # Perform similarity search
        llm = ChatOpenAI(api_key=st.secrets["OPENAI_API_KEY"], model="gpt-4-turbo-preview", temperature=0, streaming=True)
        chain = prompt | llm | StrOutputParser() 
        return chain.stream({
            "document_text": document_text,
            "user_question": user_question,
        })
    
def display_search_results(search_results):
    if not search_results:
        st.write("Geen documenten gevonden.")
        return
    
    if isinstance(search_results[0], str):
        search_results = [{'title': filename, 'path': os.path.join(BASE_DIR, filename)} for filename in search_results]

    selected_title = st.selectbox("Zoekresultaten:", [doc['title'] for doc in search_results])
    selected_document = next((doc for doc in search_results if doc['title'] == selected_title), None)
    
    if selected_document:
        user_question = st.text_input("Stel een vraag over de polisvoorwaarden:")
        if user_question:
            # Call process_document and use its return value as the argument for st.write_stream
            document_stream = process_document(selected_document['path'], user_question)
            st.write_stream(document_stream)  # Correctly pass the generator/stream to st.write_stream

        # Download button for the selected PDF file
        with open(selected_document['path'], "rb") as file:
            btn = st.download_button(
                label="Download polisvoorwaarden",
                data=file,
                file_name=selected_document['title'],
                mime="application/pdf"
            )

# Main application
def main():
    st.title("Comprehensive Insurance Tool")

    basic_prompt_rules = "Geef de samenvatting altijd in bulletpoints en niet in vol uitgeschreven zinnen. Gebruik duidelijke kopjes. De samenvatting is altijd in het Nederlands, het betreft altijd een telefoongesprek tussen twee partijen. Je zorgt altijd dat er geen belangrijke informatie wordt overgeslagen. Vermeld het onderwerp, en de sprekers."

    department_prompts = {
        "schade": "Jij bent een expert schadebehandelaar, je stelt alle relevante vragen die benodigd zijn voor het behandelen van een schade. Op deze manier verzamel je alle informatie voor het schadedossier van de klant. Je zorgt ervoor dat alle informatie met betrekking tot een schade worden opgenomen. ALTIJD moet de volgende informatie worden opgenomen: 1. Aan welk object is er schade? 2. Hoe hoog is de schade in euro's? Is de schade al hersteld? Heeft er een expert naar gekeken? Wanneer is de schade opgetreden? Onder welke polis zou deze schade kunnen vallen? Zijn er foto's of andere documentatie verstuurd? Is de schade zichtbaar vanaf de straat of meer verborgen? Analyseer in het transcript of er actiepunten zijn voor ofwel de schadebehandelaar ofwel de klant. Je houdt de samenvatting zelf kort en beperkt tot de belangrijkste details voor de context van de schade(behandeling), maar zorg er voor (dit is de grootste prioriteit) dat geen enkele gegevens met betrekking tot de schade zelf worden weggelaten. Maak simpele directe zinnen. Deze geef je weer in bullet points aan het einde van de samenvatting, je zorgt ervoor dat je dat nooit overslaat.",
        "financiele planning": "Samenvatting voor de afdeling Financiële Planning: ...",
        "adviseurs": "Samenvatting voor de afdeling Adviseurs: ...",
        "bedrijven": "Samenvatting voor de afdeling Bedrijven: ...",
        "particulieren": "Samenvatting voor de afdeling Particulieren: ...",
        "algemeen": "Algemene samenvatting: ..."
    }

    def generate_response(txt, speaker1, speaker2, subject, department, openai_api_key):
        department_prompt = department_prompts.get(department, "Algemene samenvatting: ...")
        detailed_instructions = f"{basic_prompt_rules} {department_prompt}"
        prompt_template = ChatPromptTemplate.from_template(
            f"Vat dit samen: {{transcript}} van {{speaker1}} en {{speaker2}} over {{subject}}. Met deze instructies: {detailed_instructions}"
        )
        model = ChatOpenAI(api_key=openai_api_key, model_name="gpt-4-0125-preview", temperature=0.1)
        chain = prompt_template | model | StrOutputParser()
        summary = chain.invoke({
            "transcript": txt,
            "speaker1": speaker1,
            "speaker2": speaker2,
            "subject": subject
        })
        return summary
    
    # Page 1: File Upload
    uploaded_file = st.file_uploader("Kies een MP3 bestand", type="mp3")
    if uploaded_file is not None:
        temp_dir = "temp"
        os.makedirs(temp_dir, exist_ok=True)
        temp_path = os.path.join(temp_dir, uploaded_file.name)
        with open(temp_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        st.session_state['uploaded_file'] = uploaded_file
        st.session_state['page'] = 2


    if 'page' in st.session_state and st.session_state['page'] == 2:
        # Page 2: Transcription and Editing
        st.title("Transcriberen en bewerken")
        department = st.radio("Selecteer de afdeling", list(department_prompts.keys()))
        if 'uploaded_file' in st.session_state:
            temp_path = os.path.join("temp", st.session_state['uploaded_file'].name)
            
            if st.button('Transcriberen', key='transcribe_audio'):
                with st.spinner("Transcriptie wordt gegenereerd, dit kan even duren, afhankelijk van de lengte van het gesprek..."):
                    #try:
                        #st.session_state['transcript'] = transcribe_with_whisper(temp_path)
                    #except Exception as e:
                        #st.error(f"Error during transcription: {str(e)}")
                    #os.remove(temp_path)


                    # Speechmatics transcription logic here
                    AUTH_TOKEN = st.secrets["speechmatics"]["auth_token"]
                    LANGUAGE = "nl"
                    settings = ConnectionSettings(url="https://asr.api.speechmatics.com/v2", auth_token=AUTH_TOKEN)
                    conf = {"type": "transcription", "transcription_config": {"language": LANGUAGE, "operating_point": "enhanced", "diarization": "speaker", "speaker_diarization_config": {"speaker_sensitivity": 0.2}}}
                    with BatchClient(settings) as speech_client:
                        try:
                            job_id = speech_client.submit_job(audio=temp_path, transcription_config=conf)
                            st.session_state['transcript'] = speech_client.wait_for_completion(job_id, transcription_format="txt")
                        except HTTPStatusError as e:
                            st.error(f"Error during transcription: {str(e)}")
                    os.remove(temp_path)

            if 'transcript' in st.session_state:
                edited_text = st.text_area("Edit Transcript", st.session_state['transcript'], height=1000)
                speaker1 = st.text_input("Name for Speaker 1 (S1)")
                speaker2 = st.text_input("Name for Speaker 2 (S2)")
                subject = st.text_input("Subject of the Call")
                st.session_state['edited_text'] = edited_text
                st.session_state['speaker1'] = speaker1
                st.session_state['speaker2'] = speaker2
                st.session_state['subject'] = subject
                st.session_state['department'] = department
                st.session_state['page'] = 3

    if 'page' in st.session_state and st.session_state['page'] == 3:
        # Page 3: Summary
        st.title("Samenvatting van het gesprek")
        if st.button('Genereer Samenvatting', key='generate_summary'):
            if 'edited_text' in st.session_state and 'speaker1' in st.session_state and 'speaker2' in st.session_state and 'subject' in st.session_state:
                with st.spinner("Samenvatting wordt gegenereerd, dit kan even duren afhankelijk van de lengte van het transcript..."):
                    summary = generate_response(
                        st.session_state['edited_text'],
                        st.session_state['speaker1'],
                        st.session_state['speaker2'],
                        st.session_state['subject'],
                        st.session_state["department"],
                        st.secrets["openai"]["api_key"]
                    )
                    #summary = st.text_area("Samenvatting", summary, height=1000)
                    st.markdown(summary)

    if 'page' in st.session_state and st.session_state['page'] == 4:
        st.title("Controleer de claim tegen polisvoorwaarden")

        # Step 1: Select a policy document
        all_documents = get_all_documents()
        selected_document = st.selectbox("Selecteer een polisvoorwaarden document:", [doc['title'] for doc in all_documents])

        # Step 2: Ask a question about the claim
        user_question = st.text_input("Stel een vraag over de claim:", key='coverage_question')

        # Step 3: Button to check the claim
        if st.button('Controleer Claim'):
            if user_question:
                # Find the selected document
                doc_path = next((doc['path'] for doc in all_documents if doc['title'] == selected_document), None)
                if doc_path:
                    # Process the document to check the claim
                    with st.spinner('Claim wordt gecontroleerd...'):
                        coverage_response = process_document(doc_path, user_question)
                        st.write(coverage_response)
                else:
                    st.error("Document niet gevonden.")
        
            
            



    
    







