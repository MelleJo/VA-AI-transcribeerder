import streamlit as st
import time
import base64
from services.summarization_service import summarize_text
from utils.audio_processing import process_audio_input
from utils.file_processing import process_uploaded_file
from utils.text_processing import update_gesprekslog, load_questions
from ui.components import display_transcript
from ui.pages import render_feedback_form, render_conversation_history
from openai_service import perform_gpt4_operation

def main():
    st.set_page_config(page_title="Gesprekssamenvatter", page_icon="🎙️", layout="wide")
    
    st.write("Debug: Starting main function")
    config = load_config()
    st.write("Debug: Config loaded")
    initialize_session_state()
    st.write("Debug: Session state initialized")
    
    st.title("Gesprekssamenvatter versie 0.2.5")
    st.markdown("---")

    col1, col2 = st.columns([1, 3])

    with col1:
        st.markdown("### 📋 Configuratie")
        department = st.selectbox(
            "Kies je afdeling", 
            config["DEPARTMENTS"], 
            key='department_select',
            index=config["DEPARTMENTS"].index(st.session_state.department)
        )
        st.session_state.department = department

        input_method = st.radio("Invoermethode", config["INPUT_METHODS"], key='input_method_radio')

        if department in config["DEPARTMENTS"]:
            with st.expander("💡 Vragen om te overwegen"):
                questions = load_questions(f"{department.lower().replace(' ', '_')}.txt")
                for question in questions:
                    st.markdown(f"- {question.strip()}")

    with col2:
        st.markdown("### 📝 Invoer & Samenvatting")
        
        if input_method == "Upload tekst":
            uploaded_file = st.file_uploader("Kies een bestand", type=['txt', 'docx', 'pdf'])
            if uploaded_file:
                try:
                    st.session_state.transcript = process_uploaded_file(uploaded_file)
                    st.success("Bestand succesvol geüpload en verwerkt.")
                except Exception as e:
                    st.error(f"Fout bij het verwerken van het bestand: {str(e)}")

        elif input_method == "Voer tekst in of plak tekst":
            st.session_state.input_text = st.text_area(
                "Voer tekst in:", 
                value=st.session_state.input_text, 
                height=200,
                key='input_text_area'
            )

        elif input_method in ["Upload audio", "Neem audio op"]:
            try:
                process_audio_input(input_method)
            except Exception as e:
                st.error(f"Fout bij het verwerken van audio: {str(e)}")

        if st.button("Samenvatten", key='summarize_button'):
            if st.session_state.input_text or st.session_state.transcript:
                with st.spinner("Samenvatting maken..."):
                    start_time = time.time()
                    
                    text_to_summarize = st.session_state.transcript if st.session_state.transcript else st.session_state.input_text
                    st.write(f"Debug: About to call summarize_text with text length {len(text_to_summarize)} and department {st.session_state.department}")
                    
                    try:
                        result = summarize_text(text_to_summarize, st.session_state.department)
                        st.write(f"Debug: Result from summarize_text: {result}")
                        
                        if isinstance(result, dict) and "timing_info" in result and "summary" in result:
                            timing_info = result["timing_info"]
                            new_summary = result["summary"]
                            
                            st.success(f"Proces voltooid in {timing_info['total_time']:.2f} seconden!")
                            st.info(f"Prompt voorbereiding: {timing_info['prompt_preparation']:.2f} seconden")
                            st.info(f"Model initialisatie: {timing_info['model_initialization']:.2f} seconden")
                            st.info(f"Chain creatie: {timing_info['chain_creation']:.2f} seconden")
                            st.info(f"Samenvatting generatie: {timing_info['summarization']:.2f} seconden")

                            if new_summary:
                                update_summary(new_summary)
                                update_gesprekslog(text_to_summarize, new_summary)

                                st.markdown("### 📑 Samenvatting")
                                st.markdown("""
                                <style>
                                .summary-box {
                                    border: 2px solid #4CAF50;
                                    border-radius: 10px;
                                    padding: 20px;
                                    background-color: #f1f8e9;
                                    position: relative;
                                }
                                .summary-title {
                                    position: absolute;
                                    top: -15px;
                                    left: 10px;
                                    background-color: white;
                                    padding: 0 10px;
                                    font-weight: bold;
                                }
                                .summary-buttons {
                                    position: absolute;
                                    bottom: 10px;
                                    right: 10px;
                                }
                                </style>
                                """, unsafe_allow_html=True)

                                st.markdown(f"""
                                <div class="summary-box">
                                    <div class="summary-title">Samenvatting</div>
                                    {new_summary}
                                    <div class="summary-buttons">
                                        <button onclick="copyToClipboard()">Kopieer</button>
                                        <a href="data:application/vnd.openxmlformats-officedocument.wordprocessingml.document;base64,{base64.b64encode(create_safe_docx(new_summary)).decode()}" download="samenvatting.docx">
                                            <button>Download</button>
                                        </a>
                                    </div>
                                </div>
                                """, unsafe_allow_html=True)

                                st.markdown("""
                                <script>
                                function copyToClipboard() {
                                    const el = document.createElement('textarea');
                                    el.value = document.querySelector('.summary-box').innerText;
                                    document.body.appendChild(el);
                                    el.select();
                                    document.execCommand('copy');
                                    document.body.removeChild(el);
                                    alert('Samenvatting gekopieerd naar klembord!');
                                }
                                </script>
                                """, unsafe_allow_html=True)
                                
                                render_feedback_form()
                            else:
                                st.error("Er is geen samenvatting gegenereerd. Controleer de foutmelding hierboven.")
                        else:
                            st.error(f"Onverwacht resultaat van summarize_text: {result}")
                    except Exception as e:
                        st.error(f"Er is een fout opgetreden bij het maken van de samenvatting: {str(e)}")
            else:
                st.warning("Voer alstublieft tekst in of upload een bestand om samen te vatten.")

        display_transcript(st.session_state.transcript)

        if st.session_state.summary:
            st.markdown("### 🛠️ Vervolgacties")
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                if st.button("🔍 Maak korter"):
                    with st.spinner("Samenvatting inkorten..."):
                        try:
                            new_summary = perform_gpt4_operation(st.session_state.summary, "maak de samenvatting korter en bondiger")
                            update_summary(new_summary)
                            st.success("Samenvatting is ingekort.")
                        except Exception as e:
                            st.error(f"Fout bij het inkorten van de samenvatting: {str(e)}")
            
            with col2:
                if st.button("📊 Zet om in rapport"):
                    with st.spinner("Rapport genereren..."):
                        try:
                            new_summary = perform_gpt4_operation(st.session_state.summary, "zet deze samenvatting om in een formeel rapport voor de klant")
                            update_summary(new_summary)
                            st.success("Rapport is gegenereerd.")
                        except Exception as e:
                            st.error(f"Fout bij het genereren van het rapport: {str(e)}")
            
            with col3:
                if st.button("📌 Extraheer actiepunten"):
                    with st.spinner("Actiepunten extraheren..."):
                        try:
                            new_summary = perform_gpt4_operation(st.session_state.summary, "extraheer duidelijke actiepunten uit deze samenvatting")
                            update_summary(new_summary)
                            st.success("Actiepunten zijn geëxtraheerd.")
                        except Exception as e:
                            st.error(f"Fout bij het extraheren van actiepunten: {str(e)}")
            
            st.markdown("---")
            
            custom_operation = st.text_input("🔧 Aangepaste bewerking:", key="custom_operation_input", 
                                             placeholder="Bijvoorbeeld: Voeg een conclusie toe")
            if st.button("Uitvoeren"):
                with st.spinner("Bezig met bewerking..."):
                    try:
                        new_summary = perform_gpt4_operation(st.session_state.summary, custom_operation)
                        update_summary(new_summary)
                        st.success("Aangepaste bewerking is uitgevoerd.")
                    except Exception as e:
                        st.error(f"Fout bij het uitvoeren van de aangepaste bewerking: {str(e)}")
            
            display_product_descriptions(product_descriptions)

    st.markdown("---")
    render_conversation_history()

if __name__ == "__main__":
    try:
        product_descriptions = load_product_descriptions()
        main()
    except Exception as e:
        st.error(f"Er is een onverwachte fout opgetreden: {str(e)}")
        st.write("Debug: Stacktrace:", st.exception(e))