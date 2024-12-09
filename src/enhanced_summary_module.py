# src/enhanced_summary_module.py

from openai import OpenAI
import streamlit as st
from typing import List, Dict, Union
from streamlit.runtime.uploaded_file_manager import UploadedFile
import json
from .utils import transcribe_audio
import logging

logger = logging.getLogger(__name__)

class EnhancedSummaryPipeline:
    def __init__(self, client: OpenAI):
        self.client = client
        self.mini_model = "gpt-3.5-turbo"  # Lightweight model
        self.main_model = "gpt-4"          # Full model

    def extract_topics(self, transcript: str) -> List[Dict[str, str]]:
        """
        First pass: Extract main topics from the transcript.
        """
        prompt = f"""
Analyze the following transcript and identify all distinct topics discussed in detail.
For each topic:
- Provide a clear title
- Specify the relevant parts of the transcript
- Include any numbers, dates, or specific details mentioned

Format your response as a JSON array of objects with keys 'title' and 'context'.

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
            # Try to extract JSON from the response
            json_start = response_content.find('[')
            json_end = response_content.rfind(']')
            if json_start != -1 and json_end != -1:
                json_str = response_content[json_start:json_end+1]
                return json.loads(json_str)
            else:
                st.error("Kon geen JSON extraheren uit de response in 'extract_topics'.")
                return []
        except Exception as e:
            logger.error(f"Error while extracting topics: {str(e)}")
            st.error(f"Fout bij het extraheren van onderwerpen: {str(e)}")
            return []

    def generate_detailed_summary(self, topic: Dict[str, str]) -> str:
        """
        Second pass: Generate a detailed summary for each topic.
        """
        prompt = f"""
Create a detailed summary of the following specific topic from the transcript.
Focus on:
- Specific details, numbers, and dates mentioned
- Important decisions or conclusions
- Actions or next steps related to this topic

Topic: {topic['title']}
Relevant context:
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
            logger.error(f"Error while generating detailed summary: {str(e)}")
            st.error(f"Fout bij het genereren van een gedetailleerde samenvatting: {str(e)}")
            return ""

    def validate_coverage(self, transcript: str, summaries: Dict[str, str]) -> List[str]:
        """
        Third pass: Validate coverage and identify any missed topics.
        """
        prompt = f"""
Review these summaries and the original transcript. Identify any important topics
or details that may have been missed. Focus on:
- Significant topics not covered in the summaries
- Important details that were overlooked
- Any inconsistencies between the transcript and the summaries

Summaries:
{json.dumps(summaries, indent=2)}

Original Transcript:
\"\"\"
{transcript}
\"\"\"

Provide your findings as a list of missed topics.

Format your response as a JSON array of strings.
        """
        try:
            response = self.client.chat.completions.create(
                model=self.mini_model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=1000
            )
            response_content = response.choices[0].message.content
            # Try to extract JSON from the response
            json_start = response_content.find('[')
            json_end = response_content.rfind(']')
            if json_start != -1 and json_end != -1:
                json_str = response_content[json_start:json_end+1]
                return json.loads(json_str)
            else:
                st.error("Could not extract JSON from the response in 'validate_coverage'.")
                return []
        except Exception as e:
            logger.error(f"Error while validating coverage: {str(e)}")
            st.error(f"Fout bij het valideren van de dekking: {str(e)}")
            return []

    def process_transcript(self, transcript: str, failed_chunks: bool) -> str:
        """
        Main pipeline for processing longer transcripts.
        """
        # Step 1: Extract topics
        topics = self.extract_topics(transcript)
        if not topics:
            st.error("Geen onderwerpen gevonden in het transcript.")
            return ""

        # Step 2: Generate detailed summaries for each topic
        detailed_summaries = {}
        for topic in topics:
            summary = self.generate_detailed_summary(topic)
            if summary:
                detailed_summaries[topic['title']] = summary
            else:
                st.error(f"Kon geen samenvatting genereren voor onderwerp: {topic['title']}")

        # Step 3: Validate coverage
        missed_topics = self.validate_coverage(transcript, detailed_summaries)

        # Step 4: Compile everything into a final summary
        final_summary = ""

        for topic_title, summary in detailed_summaries.items():
            final_summary += f"## {topic_title}\n{summary}\n\n"

        if missed_topics:
            final_summary += "## Aanvullende Onderwerpen\n"
            for topic in missed_topics:
                final_summary += f"- {topic}\n"

        # Add disclaimer if there were failed chunks
        if failed_chunks:
            disclaimer = (
                "\n\n**Let op:** Een deel van de transcriptie is mislukt. "
                "De nauwkeurigheid van de samenvatting kan hierdoor minder zijn "
                "of er kunnen onderdelen ontbreken."
            )
            final_summary += disclaimer

        return final_summary

def generate_enhanced_summary(audio_file: Union[str, bytes, 'UploadedFile'], client: OpenAI) -> str:
    """
    Helper function to generate enhanced summary.
    """
    pipeline = EnhancedSummaryPipeline(client)
    full_transcript, failed_chunks = transcribe_audio(audio_file)
    if full_transcript:
        return pipeline.process_transcript(full_transcript, failed_chunks)
    else:
        st.error("Er is een fout opgetreden bij het transcriberen van het audiobestand.")
        return ""
