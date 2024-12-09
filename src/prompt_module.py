# src/prompt_module.py

import streamlit as st
import streamlit_shadcn_ui as ui
from .utils import get_prompt_names, get_prompt_content

def render_prompt_selection():
    st.markdown("<h2 class='section-title'>Wat wil je doen?</h2>", unsafe_allow_html=True)

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

    if st.session_state.get('main_category') == "Langere Gesprekken":
        st.markdown("""
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
        """, unsafe_allow_html=True)
    
    main_category = st.radio("Kies een hoofdcategorie:", list(prompt_categories.keys()))
    st.session_state.main_category = main_category
    
    sub_category = st.radio("Kies een subcategorie:", list(prompt_categories[main_category].keys()))
    selected_prompt = st.selectbox("Kies een specifieke instructie:", prompt_categories[main_category][sub_category])

    proceed_btn = st.button("Verder ➔")
    if proceed_btn:
        st.session_state.selected_prompt = selected_prompt
        st.session_state.is_long_recording = main_category == "Langere Gesprekken"
        st.session_state.step = 'input_selection'
        st.rerun()