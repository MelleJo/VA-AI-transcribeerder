# src/prompt_module.py

import streamlit as st
from .utils import get_prompt_names, get_prompt_content
from src.ui_components import ui_button

def render_prompt_selection():
    st.markdown("<h2 class='section-title'>Wat wil je doen?</h2>", unsafe_allow_html=True)

    # Define categories and their corresponding prompts
    prompt_categories = {
        "Veldhuis Advies": {
            "Pensioen": ["collectief_pensioen", "deelnemersgesprekken_collectief_pensioen", "onderhoudsgesprekkenwerkgever", "pensioen"],
            "Hypotheek": ["hypotheek", "hypotheek_rapport"],
            "Financiële Planning": ["aov", "financieelplanningstraject"],
            "Overig": ["ingesproken_notitie", "telefoongesprek"]
        },
        "Veldhuis Advies Groep": {
            "Bedrijven": ["VIP", "risico_analyse", "adviesgesprek"],
            "Particulieren": ["klantrapport", "klantvraag"],
            "Schade": ["schade_beoordeling", "schademelding", "expertise_gesprek"],
            "Overig": ["mutatie", "ingesproken_notitie", "telefoongesprek"]
        },
        "NLG Arbo": {
            "Casemanager": ["casemanager"],
            "Bedrijfsarts": ["gesprek_bedrijfsarts"],
            "Overig": ["ingesproken_notitie", "telefoongesprek"]
        },
        "Langere Gesprekken": {
            "Adviesgesprekken": ["lang_adviesgesprek", "lang_hypotheekgesprek"],
            "Vergaderingen": ["notulen_vergadering", "notulen_brainstorm"],
            "Rapportages": ["uitgebreid_rapport"]
        }
    }

    # Add disclaimer for "Langere Gesprekken" category
    disclaimer_html = """
    <div class="info-banner" style="
        background-color: #f8f9fa;
        border-left: 4px solid #4CAF50;
        padding: 1rem;
        margin: 1rem 0;
        border-radius: 4px;
        font-size: 0.9rem;
    ">
        <p style="margin: 0;">
            <strong>Let op:</strong> Deze optie gebruikt geavanceerde AI-technieken voor een diepgaandere analyse 
            van langere gesprekken. De verwerking duurt hierdoor wat langer, maar levert een uitgebreidere en 
            meer gedetailleerde samenvatting op.
        </p>
    </div>
    """

    # Radio buttons for category selection with custom styling
    st.markdown("""
    <style>
    div.row-widget.stRadio > div {
        display: flex;
        flex-direction: column;
        gap: 10px;
    }
    div.row-widget.stRadio > div label {
        padding: 10px 15px;
        background-color: white;
        border: 1px solid #e0e0e0;
        border-radius: 5px;
        transition: all 0.2s;
    }
    div.row-widget.stRadio > div label:hover {
        background-color: #f8f9fa;
        border-color: #4CAF50;
    }
    </style>
    """, unsafe_allow_html=True)
    
    main_category = st.radio("Kies een hoofdcategorie:", list(prompt_categories.keys()))
    
    # Show disclaimer if "Langere Gesprekken" is selected
    if main_category == "Langere Gesprekken":
        st.markdown(disclaimer_html, unsafe_allow_html=True)
    
    sub_category = st.radio("Kies een subcategorie:", list(prompt_categories[main_category].keys()))
    
    # Dropdown for prompt selection
    selected_prompt = st.selectbox("Kies een specifieke instructie:", prompt_categories[main_category][sub_category])

    # Button to proceed
    def on_proceed_click():
        proceed(selected_prompt, main_category)

    if ui_button("Verder ➔", on_click=on_proceed_click, key="proceed_button"):
        pass

def proceed(selected_prompt, main_category):
    st.session_state.selected_prompt = selected_prompt
    # Store whether this is a long recording prompt
    st.session_state.is_long_recording = main_category == "Langere Gesprekken"
    st.session_state.step = 'input_selection'
    st.rerun()
