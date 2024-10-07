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
AUDIO_SEGMENT_LENGTH = 60000  # 30 seconds in milliseconds

# Email Configuration
EMAIL_SENDER = st.secrets["email"]["username"]
EMAIL_PASSWORD = st.secrets["email"]["password"]
EMAIL_SMTP_SERVER = st.secrets["email"]["smtp_server"]
EMAIL_SMTP_PORT = st.secrets["email"]["smtp_port"]

# Colleague email addresses
COLLEAGUE_EMAILS = st.secrets["colleague_emails"]

# Prompt Reminders
PROMPT_REMINDERS = {
    "hypotheek_rapport": [
        {"topic": "Financiële Situatie", "details": ["Inkomen (bruto/netto)", "Vaste lasten", "Schulden", "Spaargeld", "Beleggingen"]},
        {"topic": "Woninggegevens", "details": ["Type woning", "Bouwjaar", "WOZ-waarde", "Energielabel", "Staat van onderhoud", "Erfpacht"]},
        {"topic": "Hypotheekwensen", "details": ["Gewenst hypotheekbedrag", "Looptijd", "Rentevaste periode", "Aflossingsvorm", "Overbruggingskrediet"]},
        {"topic": "Toekomstplannen", "details": ["Gezinsuitbreiding", "Carrièreveranderingen", "Verbouwingsplannen", "Verhuisplannen"]},
        {"topic": "Risico's", "details": ["Arbeidsongeschiktheid", "Werkloosheid", "Overlijden", "Echtscheiding", "Pensioen"]},
        {"topic": "Overige Aspecten", "details": ["Studieschulden", "Partneralimentatie", "Eigen bedrijf", "Tweede woning"]}
    ],
    "pensioen": [
        {"topic": "Huidige Situatie", "details": ["Leeftijd", "Dienstjaren", "Opgebouwde pensioenrechten", "AOW-leeftijd", "Huidige pensioenregeling"]},
        {"topic": "Pensioenwensen", "details": ["Gewenste pensioenleeftijd", "Beoogd pensioeninkomen", "Parttime werken", "Reisplannen", "Hobby's"]},
        {"topic": "Aanvullende Voorzieningen", "details": ["Lijfrentes", "Beleggingen", "Spaargeld", "Overwaarde woning", "Erfenissen"]},
        {"topic": "Risico's", "details": ["Arbeidsongeschiktheid", "Overlijden", "Langleven", "Inflatie", "Zorgkosten"]},
        {"topic": "Partner", "details": ["Inkomen partner", "Pensioenopbouw partner", "Nabestaandenpensioen", "Leeftijdsverschil"]},
        {"topic": "Fiscale Aspecten", "details": ["Jaarruimte", "Reserveringsruimte", "Box 3 vermogen", "Hypotheekrenteaftrek"]}
    ],
    "aov": [
        {"topic": "Beroep en Inkomen", "details": ["Exacte beroepsomschrijving", "Jaarinkomen", "Vaste/variabele componenten", "Nevenactiviteiten"]},
        {"topic": "Gezondheid", "details": ["Huidige gezondheidssituatie", "Medische voorgeschiedenis", "Levensstijl", "Sporten/hobby's"]},
        {"topic": "Bedrijfssituatie", "details": ["Rechtsvorm", "Aantal medewerkers", "Bedrijfsrisico's", "Branchespecifieke risico's"]},
        {"topic": "Gewenste Dekking", "details": ["Verzekerd bedrag", "Eigenrisicoperiode", "Eindleeftijd", "Indexering", "Uitkeringsdrempel"]},
        {"topic": "Financiële Situatie", "details": ["Vaste lasten", "Spaargeld", "Andere inkomstenbronnen", "Vermogen", "Schulden"]},
        {"topic": "Bestaande Voorzieningen", "details": ["Huidige verzekeringen", "Pensioenopbouw", "Arbeidsongeschiktheidsvoorzieningen via werkgever"]}
    ],
    "zakelijke_risico_analyse": [
        {"topic": "Bedrijfsinformatie", "details": ["Branche", "Omvang", "Rechtsvorm", "Jaren actief", "Vestigingslocatie(s)"]},
        {"topic": "Financiële Risico's", "details": ["Omzet", "Winst", "Debiteuren", "Crediteuren", "Liquiditeit", "Investeringen"]},
        {"topic": "Operationele Risico's", "details": ["Bedrijfsmiddelen", "Voorraadbeheer", "Logistiek", "IT-systemen", "Bedrijfsprocessen"]},
        {"topic": "Personeelsrisico's", "details": ["Aantal medewerkers", "Sleutelfiguren", "Verzuim", "Aansprakelijkheid", "Arbeidsongeschiktheid"]},
        {"topic": "Externe Risico's", "details": ["Marktpositie", "Concurrentie", "Wet- en regelgeving", "Economische factoren", "Technologische ontwikkelingen"]},
        {"topic": "Specifieke Bedrijfsrisico's", "details": ["Productaansprakelijkheid", "Milieurisico's", "Cybercrime", "Bedrijfsonderbreking", "Fraude"]}
    ],
    "onderhoudsadviesgesprek": [
        {"topic": "Huidige Verzekeringssituatie", "details": ["Overzicht polissen", "Dekkingen", "Premies", "Voorwaarden", "Eigen risico's"]},
        {"topic": "Veranderingen Persoonlijke Situatie", "details": ["Gezinssamenstelling", "Woning", "Inkomen", "Gezondheid", "Hobby's/sporten"]},
        {"topic": "Veranderingen Zakelijke Situatie", "details": ["Bedrijfsgroei", "Nieuwe activiteiten", "Personeel", "Omzet", "Bedrijfsmiddelen"]},
        {"topic": "Toekomstplannen", "details": ["Investeringen", "Uitbreiding", "Bedrijfsoverdracht", "Pensioen", "Emigratie"]},
        {"topic": "Risicobeoordeling", "details": ["Nieuwe risico's", "Veranderde risico's", "Risicobereidheid", "Claimhistorie", "Preventiemaatregelen"]},
        {"topic": "Markt en Concurrentie", "details": ["Nieuwe verzekeringsproducten", "Prijsontwikkelingen", "Concurrerende aanbiedingen"]}
    ],
    "expertise_gesprek": [
        {"topic": "Schadegegevens", "details": ["Datum en tijdstip schade", "Locatie", "Betrokken partijen", "Schadeoorzaak"]},
        {"topic": "Schadeomvang", "details": ["Zichtbare schade", "Verborgen schade", "Gevolgschade", "Exacte metingen"]},
        {"topic": "Verzekeringsinformatie", "details": ["Polisnummer", "Dekking", "Eigen risico", "Uitsluitingen"]},
        {"topic": "Documentatie", "details": ["Foto's", "Video's", "Getuigenverklaringen", "Expertiserapporten"]},
        {"topic": "Herstel en Reparatie", "details": ["Mogelijkheden tot herstel", "Geschatte kosten", "Tijdsduur", "Aanbevolen bedrijven"]},
        {"topic": "Preventiemaatregelen", "details": ["Oorzaakanalyse", "Aanbevelingen ter voorkoming", "Risicobeperkende maatregelen"]}
    ],
    "financieel_planningstraject": [
        {"topic": "Persoonlijke Doelen", "details": ["Korte termijn doelen", "Lange termijn doelen", "Droomscenario's", "Prioriteiten"]},
        {"topic": "Inkomsten en Uitgaven", "details": ["Huidige inkomsten", "Verwachte inkomstenontwikkeling", "Vaste lasten", "Leefgeld"]},
        {"topic": "Vermogen en Schulden", "details": ["Spaartegoeden", "Beleggingen", "Onroerend goed", "Hypotheek", "Overige schulden"]},
        {"topic": "Pensioen en AOW", "details": ["Opgebouwde pensioenrechten", "Pensioengat", "AOW-leeftijd", "Gewenste pensioenleeftijd"]},
        {"topic": "Risico's en Verzekeringen", "details": ["Overlijdensrisico", "Arbeidsongeschiktheid", "Werkloosheid", "Zorgkosten"]},
        {"topic": "Fiscale Aspecten", "details": ["Belastingvoordelen", "Aftrekposten", "Vermogensrendementsheffing", "Schenkingen/erfenissen"]}
    ],
    "ingesproken_notitie": [
        {"topic": "Context", "details": ["Aanleiding voor de notitie", "Betrokken personen/afdelingen", "Datum en tijd"]},
        {"topic": "Hoofdpunten", "details": ["Kernboodschap", "Belangrijkste bevindingen", "Conclusies"]},
        {"topic": "Actiepunten", "details": ["Concrete taken", "Verantwoordelijken", "Deadlines"]},
        {"topic": "Vervolgstappen", "details": ["Geplande vergaderingen", "Benodigde beslissingen", "Verwachte resultaten"]},
        {"topic": "Aandachtspunten", "details": ["Potentiële problemen", "Openstaande vragen", "Benodigde middelen"]},
        {"topic": "Overige Informatie", "details": ["Relevante documenten", "Contactpersonen", "Budgetoverwegingen"]}
    ],
    "telefoongesprek": [
        {"topic": "Gesprekspartner", "details": ["Naam", "Functie", "Bedrijf", "Contactgegevens"]},
        {"topic": "Aanleiding", "details": ["Reden voor het gesprek", "Voorgeschiedenis", "Verwachtingen"]},
        {"topic": "Besproken Onderwerpen", "details": ["Hoofdthema's", "Standpunten", "Vragen en antwoorden"]},
        {"topic": "Afspraken", "details": ["Gemaakte toezeggingen", "Deadlines", "Vervolgacties"]},
        {"topic": "Sfeer en Toon", "details": ["Algemene indruk", "Houding gesprekspartner", "Gevoelige punten"]},
        {"topic": "Vervolgstappen", "details": ["Geplande follow-up", "Te versturen informatie", "Volgende contactmoment"]}
    ],
    "adviesgesprek": [
        {"topic": "Klantsituatie", "details": ["Huidige situatie", "Behoeften en wensen", "Financiële doelstellingen"]},
        {"topic": "Productinformatie", "details": ["Besproken producten", "Voor- en nadelen", "Vergelijkingen"]},
        {"topic": "Risicoprofiel", "details": ["Risicobereidheid", "Kennis en ervaring", "Financiële draagkracht"]},
        {"topic": "Advies", "details": ["Kernpunten van het advies", "Onderbouwing", "Alternatieven"]},
        {"topic": "Kosten en Vergoedingen", "details": ["Productkosten", "Advieskosten", "Lopende kosten"]},
        {"topic": "Vervolgstappen", "details": ["Bedenktijd", "Aanvraagprocedure", "Benodigde documenten"]}
    ],
    "schademelding": [
        {"topic": "Schadegegevens", "details": ["Datum en tijd van de schade", "Locatie", "Betrokkenen"]},
        {"topic": "Schadebeschrijving", "details": ["Oorzaak", "Omvang", "Gedetailleerde beschrijving"]},
        {"topic": "Verzekeringsinformatie", "details": ["Polisnummer", "Soort verzekering", "Dekking"]},
        {"topic": "Documentatie", "details": ["Foto's", "Getuigenverklaringen", "Politierapport"]},
        {"topic": "Eerste Acties", "details": ["Genomen noodmaatregelen", "Contacten met derden", "Voorlopige reparaties"]},
        {"topic": "Vervolgstappen", "details": ["Expertise nodig?", "Verwachte herstelkosten", "Termijn afhandeling"]}
    ],
    "schade_beoordeling": [
        {"topic": "Schadedetails", "details": ["Schadedatum", "Schadeoorzaak", "Schadelocatie", "Betrokkenen"]},
        {"topic": "Polisgegevens", "details": ["Polisnummer", "Verzekeringnemer", "Dekkingsomvang", "Uitsluitingen"]},
        {"topic": "Schade-inventarisatie", "details": ["Materiele schade", "Letselschade", "Gevolgschade"]},
        {"topic": "Expertiserapport", "details": ["Bevindingen expert", "Foto's en bewijsmateriaal", "Hersteladvies"]},
        {"topic": "Aansprakelijkheid", "details": ["Schuldvraag", "Medeschuld", "Juridische aspecten"]},
        {"topic": "Uitkeringsvoorstel", "details": ["Schadebedrag", "Eigen risico", "Afschrijvingen", "Uitkeringswijze"]}
    ],
    "collectief_pensioen": [
        {"topic": "Bedrijfsgegevens", "details": ["Sector", "Aantal werknemers", "Loonsom", "CAO"]},
        {"topic": "Huidige Regeling", "details": ["Type regeling", "Pensioenuitvoerder", "Dekkingen", "Kosten"]},
        {"topic": "Werknemersbestand", "details": ["Leeftijdsopbouw", "Salarisschalen", "Parttimers", "Directie"]},
        {"topic": "Wensen Werkgever", "details": ["Budgetruimte", "Risicobereidheid", "Flexibiliteit", "Communicatie"]},
        {"topic": "Wettelijke Aspecten", "details": ["Wet toekomst pensioenen", "Fiscale grenzen", "Zorgplicht", "Overgangsregelingen"]},
        {"topic": "Toekomstvisie", "details": ["Groeiverwachtingen", "Reorganisatieplannen", "Internationale expansie"]}
    ],
    "onderhoudsgesprekkenwerkgever": [
        {"topic": "Bedrijfssituatie", "details": ["Financiële positie", "Personeelsverloop", "Organisatiewijzigingen"]},
        {"topic": "Pensioenregeling", "details": ["Wijzigingen in regeling", "Dekkingsgraad", "Indexatie", "Kosten"]},
        {"topic": "Wet Toekomst Pensioenen", "details": ["Implementatieplan", "Keuzes werkgever", "Communicatieplan"]},
        {"topic": "Arbeidsvoorwaarden", "details": ["CAO-ontwikkelingen", "Secundaire voorwaarden", "Beloningsbeleid"]},
        {"topic": "Risicomanagement", "details": ["Verzuimbeleid", "Arbeidsongeschiktheidsrisico's", "Cyberrisico's"]},
        {"topic": "Toekomstplannen", "details": ["Strategische doelen", "Verwachte groei/krimp", "Innovatieplannen"]}
    ],
    "gesprek_bedrijfsarts": [
        {"topic": "Werknemer Gegevens", "details": ["Naam", "Functie", "Afdeling", "Dienstjaren"]},
        {"topic": "Verzuimgegevens", "details": ["Eerste verzuimdag", "Verzuimfrequentie", "Verzuimoorzaak"]},
        {"topic": "Medische Situatie", "details": ["Hoofdklachten", "Behandeling", "Prognose", "Beperkingen"]},
        {"topic": "Werksituatie", "details": ["Werkzaamheden", "Werkomstandigheden", "Werkdruk", "Conflicten"]},
        {"topic": "Re-integratie", "details": ["Mogelijkheden aangepast werk", "Opbouwschema", "Interventies"]},
        {"topic": "Vervolgafspraken", "details": ["Volgende consult", "Actiepunten werkgever", "Actiepunten werknemer"]}
    ],
    "risico_analyse": [
        {"topic": "Bedrijfsprofiel", "details": ["Activiteiten", "Omvang", "Locaties", "Juridische structuur"]},
        {"topic": "Financiële Risico's", "details": ["Kredietrisico", "Liquiditeitsrisico", "Marktrisico", "Valutarisico"]},
        {"topic": "Operationele Risico's", "details": ["Bedrijfsonderbreking", "IT-uitval", "Productiefouten", "Fraude"]},
        {"topic": "Strategische Risico's", "details": ["Concurrentiepositie", "Technologische ontwikkelingen", "Reputatieschade"]},
        {"topic": "Compliance Risico's", "details": ["Wet- en regelgeving", "Vergunningen", "Ethische kwesties"]},
        {"topic": "Risicobeheer", "details": ["Huidige maatregelen", "Verzekeringen", "Risicobereidheid", "Verbetervoorstellen"]}
    ],
    "klantrapport": [
        {"topic": "Bedrijfsinformatie", "details": ["Bedrijfsnaam", "Branche", "Omvang", "Vestigingen"]},
        {"topic": "Verzekeringsportefeuille", "details": ["Overzicht polissen", "Dekkingen", "Premies", "Voorwaarden"]},
        {"topic": "Risico-inventarisatie", "details": ["Geïdentificeerde risico's", "Risicobereidheid", "Beheersmaatregelen"]},
        {"topic": "Claimhistorie", "details": ["Recente claims", "Schadestatistiek", "Preventieve maatregelen"]},
        {"topic": "Marktanalyse", "details": ["Benchmarking", "Trends in de branche", "Concurrentiepositie"]},
        {"topic": "Advies en Aanbevelingen", "details": ["Verzekeringsadvies", "Risicobeheer advies", "Kostenbesparingen"]}
    ],
    "klantvraag": [
        {"topic": "Klantgegevens", "details": ["Naam", "Bedrijf", "Functie", "Contactgegevens"]},
        {"topic": "Vraag/Probleem", "details": ["Kernvraag", "Achtergrond", "Urgentie", "Eerdere acties"]},
        {"topic": "Relevante Polisgegevens", "details": ["Betrokken verzekeringen", "Dekkingen", "Uitsluitingen"]},
        {"topic": "Gegeven Antwoord", "details": ["Kernpunten van het antwoord", "Onderbouwing", "Vervolgstappen"]},
        {"topic": "Klanttevredenheid", "details": ["Reactie klant", "Openstaande vragen", "Feedback"]},
        {"topic": "Follow-up", "details": ["Geplande acties", "Deadlines", "Verantwoordelijke medewerker"]}
    ],
    "mutatie": [
        {"topic": "Klantgegevens", "details": ["Naam", "Polisnummer", "Ingangsdatum mutatie"]},
        {"topic": "Soort Mutatie", "details": ["Type wijziging", "Betrokken verzekering(en)", "Reden voor mutatie"]},
        {"topic": "Oude Situatie", "details": ["Huidige dekking", "Premie", "Voorwaarden"]},
        {"topic": "Nieuwe Situatie", "details": ["Gewenste dekking", "Nieuwe premie", "Aangepaste voorwaarden"]},
        {"topic": "Financiële Impact", "details": ["Premieverschil", "Eventuele kosten", "Restituties"]},
        {"topic": "Vervolgstappen", "details": ["Benodigde documenten", "Verwerkingstijd", "Bevestiging naar klant"]}
    ]
}