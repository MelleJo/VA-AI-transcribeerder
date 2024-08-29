import os

# Set the base directory relative to where config.py is located
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

# Define the prompts directory relative to the base directory
PROMPTS_DIR = os.path.join(BASE_DIR, 'prompts')
QUESTIONS_DIR = os.path.join(BASE_DIR, 'questions')

DEPARTMENTS = [
    "Bedrijven", "Financieel Advies", "Schadeafdeling", "Algemeen", "Arbo", "Algemene samenvatting",
    "Ondersteuning Bedrijfsarts", "Onderhoudsadviesgesprek in tabelvorm", "Notulen van een vergadering",
    "Verslag van een telefoongesprek", "Deelnemersgesprekken collectief pensioen", "test-prompt (alleen voor Melle!)"
]

INPUT_METHODS = ["Voer tekst in of plak tekst", "Upload tekst", "Upload audio", "Neem audio op"]

def load_config():
    return {
        "PROMPTS_DIR": PROMPTS_DIR,
        "QUESTIONS_DIR": QUESTIONS_DIR,
        "DEPARTMENTS": DEPARTMENTS,
        "INPUT_METHODS": INPUT_METHODS,
    }
