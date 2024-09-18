import streamlit as st
import os

# API Configuration
OPENAI_API_KEY = st.secrets["OPENAI_API_KEY"]

# Input Configuration
ALLOWED_AUDIO_TYPES = ["mp3", "wav", "ogg", "m4a", "mp4"]
ALLOWED_TEXT_TYPES = ["txt", "pdf", "docx"]

# Prompt Configuration
PROMPTS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "prompts")

# UI Configuration
THEME_COLOR = "#3B82F6"

# AI Configuration
AUDIO_MODEL = "whisper-1"
SUMMARY_MODEL = "gpt-4o-2024-08-06"
MAX_TOKENS = 14000
TEMPERATURE = 0.3
TOP_P = 0.95
FREQUENCY_PENALTY = 0.2
PRESENCE_PENALTY = 0.1
AUDIO_SEGMENT_LENGTH = 30000  # 30 seconds in milliseconds

# Prompt Reminders
PROMPT_REMINDERS = {
    "hypotheek_rapport": [
        {"topic": "Financiële Situatie", "details": ["Inkomen", "Schulden", "Spaargeld", "Maandelijkse lasten"]},
        {"topic": "Woninggegevens", "details": ["Type woning", "Waarde", "Energielabel", "Staat van onderhoud"]},
        {"topic": "Hypotheekwensen", "details": ["Gewenst hypotheekbedrag", "Looptijd", "Rentevaste periode"]},
        {"topic": "Toekomstplannen", "details": ["Gezinsuitbreiding", "Carrièreveranderingen", "Verbouwingsplannen"]},
        {"topic": "Risico's", "details": ["Arbeidsongeschiktheid", "Werkloosheid", "Overlijden", "Echtscheiding"]}
    ],
    "pensioen": [
        {"topic": "Huidige Situatie", "details": ["Leeftijd", "Dienstjaren", "Opgebouwde pensioenrechten", "AOW-leeftijd"]},
        {"topic": "Pensioenwensen", "details": ["Gewenste pensioenleeftijd", "Beoogd pensioeninkomen", "Parttime werken"]},
        {"topic": "Aanvullende Voorzieningen", "details": ["Lijfrentes", "Beleggingen", "Spaargeld", "Overwaarde woning"]},
        {"topic": "Risico's", "details": ["Arbeidsongeschiktheid", "Overlijden", "Langleven", "Inflatie"]},
        {"topic": "Partner", "details": ["Inkomen partner", "Pensioenopbouw partner", "Nabestaandenpensioen"]}
    ],
    "aov": [
        {"topic": "Beroep en Inkomen", "details": ["Exacte beroepsomschrijving", "Jaarinkomen", "Vaste/variabele componenten"]},
        {"topic": "Gezondheid", "details": ["Huidige gezondheidssituatie", "Medische voorgeschiedenis", "Levensstijl"]},
        {"topic": "Bedrijfssituatie", "details": ["Rechtsvorm", "Aantal medewerkers", "Bedrijfsrisico's"]},
        {"topic": "Gewenste Dekking", "details": ["Verzekerd bedrag", "Eigenrisicoperiode", "Eindleeftijd"]},
        {"topic": "Financiële Situatie", "details": ["Vaste lasten", "Spaargeld", "Andere inkomstenbronnen"]}
    ],
    "zakelijke_risico_analyse": [
        {"topic": "Bedrijfsinformatie", "details": ["Branche", "Omvang", "Rechtsvorm", "Jaren actief"]},
        {"topic": "Financiële Risico's", "details": ["Omzet", "Winst", "Debiteuren", "Crediteuren", "Liquiditeit"]},
        {"topic": "Operationele Risico's", "details": ["Bedrijfsmiddelen", "Voorraadbeheer", "Logistiek", "IT-systemen"]},
        {"topic": "Personeelsrisico's", "details": ["Aantal medewerkers", "Sleutelfiguren", "Verzuim", "Aansprakelijkheid"]},
        {"topic": "Externe Risico's", "details": ["Marktpositie", "Concurrentie", "Wet- en regelgeving", "Economische factoren"]}
    ],
    "onderhoudsadviesgesprek": [
        {"topic": "Huidige Verzekeringssituatie", "details": ["Overzicht polissen", "Dekkingen", "Premies", "Voorwaarden"]},
        {"topic": "Veranderingen Persoonlijke Situatie", "details": ["Gezinssamenstelling", "Woning", "Inkomen", "Gezondheid"]},
        {"topic": "Veranderingen Zakelijke Situatie", "details": ["Bedrijfsgroei", "Nieuwe activiteiten", "Personeel", "Omzet"]},
        {"topic": "Toekomstplannen", "details": ["Investeringen", "Uitbreiding", "Bedrijfsoverdracht", "Pensioen"]},
        {"topic": "Risicobeoordeling", "details": ["Nieuwe risico's", "Veranderde risico's", "Risicobereidheid"]}
    ]
}