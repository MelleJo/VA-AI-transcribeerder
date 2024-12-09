import streamlit as st
import streamlit_shadcn_ui as ui
from .utils import get_prompt_names, get_prompt_content

def render_prompt_selection():
    ui.heading("Wat wil je doen?", level=2)

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

    # Longere Gesprekken disclaimer
    if 'main_category' in st.session_state and st.session_state.main_category == "Langere Gesprekken":
        with ui.card(className="mb-4"):
            ui.text("Let op: Deze optie gebruikt geavanceerde AI-technieken voor een diepgaandere analyse van langere gesprekken. De verwerking duurt hierdoor wat langer, maar levert een uitgebreidere en meer gedetailleerde samenvatting op.", size="sm")

    # Category selection
    main_category = ui.tabs(
        options=list(prompt_categories.keys()),
        default_value=list(prompt_categories.keys())[0],
        key="main_category_tabs"
    )
    
    if main_category:
        st.session_state.main_category = main_category
        
        # Subcategory selection
        subcategories = list(prompt_categories[main_category].keys())
        sub_category = ui.select(
            options=subcategories,
            label="Kies een subcategorie",
            placeholder="Selecteer een subcategorie...",
            key="subcategory_select"
        )
        
        if sub_category:
            # Prompt selection
            prompts = prompt_categories[main_category][sub_category]
            selected_prompt = ui.select(
                options=prompts,
                label="Kies een specifieke instructie",
                placeholder="Selecteer een instructie...",
                key="prompt_select"
            )
            
            if selected_prompt:
                proceed_btn = ui.button(
                    text="Verder ➔",
                    key="proceed_button"
                )
                
                if proceed_btn:
                    proceed(selected_prompt, main_category)

def proceed(selected_prompt, main_category):
    st.session_state.selected_prompt = selected_prompt
    st.session_state.is_long_recording = main_category == "Langere Gesprekken"
    st.session_state.step = 'input_selection'
    st.rerun()