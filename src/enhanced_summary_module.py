# src/enhanced_summary_module.py

from openai import OpenAI
import streamlit as st
from typing import List, Dict, Tuple, Union
from streamlit.runtime.uploaded_file_manager import UploadedFile
import json
from src.utils import transcribe_audio

class EnhancedSummaryPipeline:
    def __init__(self, client: OpenAI):
        self.client = client
        self.mini_model = "gpt-4o-mini"  # Lightweight model
        self.main_model = "gpt-4o"          # Full model

    def extract_topics(self, transcript: str) -> List[Dict[str, str]]:
        """First pass: Extract main topics from transcript"""
        prompt = f"""
Analyseer dit transcript en identificeer alle afzonderlijke onderwerpen die in detail zijn besproken.
Voor elk onderwerp:
- Geef een duidelijke titel
- Benoem de relevante delen van het transcript
- Neem eventuele genoemde nummers, data of specifieke details op

Formatteer je reactie als een JSON-array van objecten met de sleutels 'title' en 'context'.

Transcript:
\"\"\"
{transcript}
\"\"\"
        """
        
        try:
            response = self.client.chat.completions.create(
                model=self.mini_model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=1500
            )
            
            response_content = response.choices[0].message.content
            # Probeer JSON uit de response te extraheren
            json_start = response_content.find('[')
            json_end = response_content.rfind(']')
            if json_start != -1 and json_end != -1:
                json_str = response_content[json_start:json_end+1]
                return json.loads(json_str)
            else:
                st.error("Kon geen JSON extraheren uit de response in 'extract_topics'.")
                return []
        except Exception as e:
            st.error(f"Fout bij het extraheren van onderwerpen: {str(e)}")
            return []

    def generate_detailed_summary(self, topic: Dict[str, str]) -> str:
        """Second pass: Generate detailed summary for each topic"""
        prompt = f"""
Maak een gedetailleerde samenvatting van dit specifieke onderwerp uit het transcript.
Focus op:
- Specifieke details, nummers en data die zijn genoemd
- Belangrijke beslissingen of conclusies
- Acties of volgende stappen gerelateerd aan dit onderwerp

Onderwerp: {topic['title']}
Relevante context:
\"\"\"
{topic['context']}
\"\"\"
        """
        
        try:
            response = self.client.chat.completions.create(
                model=self.main_model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.5,
                max_tokens=1500
            )
            
            return response.choices[0].message.content.strip()
        except Exception as e:
            st.error(f"Fout bij het genereren van een gedetailleerde samenvatting: {str(e)}")
            return ""

    def validate_coverage(self, transcript: str, summaries: Dict[str, str]) -> List[str]:
        """Third pass: Validate coverage and identify any missed topics"""
        prompt = f"""
Beoordeel deze samenvattingen en het originele transcript. Identificeer eventuele belangrijke onderwerpen
of details die mogelijk zijn gemist. Focus op:
- Belangrijke onderwerpen die niet zijn behandeld in de samenvattingen
- Significante details die over het hoofd zijn gezien
- Eventuele inconsistenties tussen het transcript en de samenvattingen

Samenvattingen:
{json.dumps(summaries, indent=2)}

Origineel Transcript:
\"\"\"
{transcript}
\"\"\"

Geef je bevindingen als een lijst van gemiste onderwerpen.

Formatteer je reactie als een JSON-array van strings.
        """
        
        try:
            response = self.client.chat.completions.create(
                model=self.mini_model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=1000
            )
            
            response_content = response.choices[0].message.content
            # Probeer JSON uit de response te extraheren
            json_start = response_content.find('[')
            json_end = response_content.rfind(']')
            if json_start != -1 and json_end != -1:
                json_str = response_content[json_start:json_end+1]
                return json.loads(json_str)
            else:
                st.error("Kon geen JSON extraheren uit de response in 'validate_coverage'.")
                return []
        except Exception as e:
            st.error(f"Fout bij het valideren van de dekking: {str(e)}")
            return []

    def process_transcript(self, transcript: str, failed_chunks: bool) -> str:
        """Main pipeline for processing longer transcripts"""
        # Stap 1: Onderwerpen extraheren
        topics = self.extract_topics(transcript)
        
        # Stap 2: Gedetailleerde samenvattingen genereren voor elk onderwerp
        detailed_summaries = {}
        for topic in topics:
            detailed_summaries[topic['title']] = self.generate_detailed_summary(topic)
        
        # Stap 3: Dekking valideren
        missed_topics = self.validate_coverage(transcript, detailed_summaries)
        
        # Stap 4: Alles samenvoegen tot een definitieve samenvatting
        final_summary = ""
        
        for topic_title, summary in detailed_summaries.items():
            final_summary += f"## {topic_title}\n{summary}\n\n"
        
        if missed_topics:
            final_summary += "## Aanvullende Onderwerpen\n"
            for topic in missed_topics:
                final_summary += f"- {topic}\n"
        
        # Disclaimer toevoegen als er gefaalde chunks zijn
        if failed_chunks:
            disclaimer = (
                "\n\n**Let op:** Een deel van de transcriptie is gefaald. "
                "De nauwkeurigheid van de samenvatting kan hierdoor minder zijn "
                "of er kunnen onderdelen ontbreken."
            )
            final_summary += disclaimer

        return final_summary

def generate_enhanced_summary(audio_file: Union[str, bytes, 'UploadedFile'], client: OpenAI) -> str:
    """Helper function to generate enhanced summary"""
    pipeline = EnhancedSummaryPipeline(client)
    full_transcript, failed_chunks = transcribe_audio(audio_file)
    return pipeline.process_transcript(full_transcript, failed_chunks)
