import os

# Base directory
BASE_DIR = os.path.abspath(os.path.dirname(__file__))

# Directory configurations
PROMPTS_DIR = os.path.join(BASE_DIR, 'prompts')
QUESTIONS_DIR = os.path.join(BASE_DIR, 'questions')
AUDIO_OUTPUT_DIR = os.path.join(BASE_DIR, 'audio_output')
SUMMARY_OUTPUT_DIR = os.path.join(BASE_DIR, 'summary_output')

# Application settings
APP_TITLE = "Gesprekssamenvatter"
APP_ICON = "🎙️"
APP_LAYOUT = "wide"

# User interface settings
DEPARTMENTS = [
    "Bedrijven", "Financieel Advies", "Schadeafdeling", "Algemeen", "Arbo", "Algemene samenvatting",
    "Ondersteuning Bedrijfsarts", "Onderhoudsadviesgesprek in tabelvorm", "Notulen van een vergadering",
    "Verslag van een telefoongesprek", "Deelnemersgesprekken collectief pensioen", "test-prompt (alleen voor Melle!)"
]

INPUT_METHODS = [
    "Voer tekst in of plak tekst",
    "Upload tekst",
    "Upload audio",
    "Neem audio op"
]

# File processing settings
ALLOWED_TEXT_EXTENSIONS = ['.txt', '.docx', '.pdf']
ALLOWED_AUDIO_EXTENSIONS = ['.mp3', '.wav', '.m4a']
FILE_ENCODING = 'utf-8'

# OpenAI settings
OPENAI_MODEL = "gpt-4"
OPENAI_TEMPERATURE = 0

def load_config():
    return {
        "BASE_DIR": BASE_DIR,
        "PROMPTS_DIR": PROMPTS_DIR,
        "QUESTIONS_DIR": QUESTIONS_DIR,
        "AUDIO_OUTPUT_DIR": AUDIO_OUTPUT_DIR,
        "SUMMARY_OUTPUT_DIR": SUMMARY_OUTPUT_DIR,
        "APP_TITLE": APP_TITLE,
        "APP_ICON": APP_ICON,
        "APP_LAYOUT": APP_LAYOUT,
        "DEPARTMENTS": DEPARTMENTS,
        "INPUT_METHODS": INPUT_METHODS,
        "ALLOWED_TEXT_EXTENSIONS": ALLOWED_TEXT_EXTENSIONS,
        "ALLOWED_AUDIO_EXTENSIONS": ALLOWED_AUDIO_EXTENSIONS,
        "FILE_ENCODING": FILE_ENCODING,
        "OPENAI_MODEL": OPENAI_MODEL,
        "OPENAI_TEMPERATURE": OPENAI_TEMPERATURE,
    }
