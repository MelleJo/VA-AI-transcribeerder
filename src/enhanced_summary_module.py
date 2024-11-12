# src/enhanced_summary_module.py

from openai import OpenAI
import streamlit as st
from typing import List, Dict, Tuple
import json

class EnhancedSummaryPipeline:
    def __init__(self, client: OpenAI):
        self.client = client
        self.mini_model = "gpt-4o-mini"  # Lightweight model
        self.main_model = "gpt-4o"       # Full model

    def extract_topics(self, transcript: str) -> List[Dict[str, str]]:
        """First pass: Extract main topics from transcript"""
        prompt = f"""
        Analyze this transcript and identify all distinct topics that were discussed in detail.
        For each topic:
        - Provide a clear title
        - Identify the relevant parts of the transcript
        - Include any mentioned numbers, dates, or specific details
        
        Format your response as a JSON array of objects with 'title' and 'context' keys.
        
        Transcript:
        {transcript}
        """
        
        try:
            response = self.client.chat.completions.create(
                model=self.mini_model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                response_format={ "type": "json_object" }
            )
            
            response_content = response.choices[0].message.content
            try:
                return json.loads(response_content)["topics"]
            except json.JSONDecodeError as e:
                st.error(f"Error parsing JSON response: {str(e)}")
                return []
        except Exception as e:
            st.error(f"Error extracting topics: {str(e)}")
            return []

    def generate_detailed_summary(self, topic: Dict[str, str]) -> str:
        """Second pass: Generate detailed summary for each topic"""
        prompt = f"""
        Create a detailed summary of this specific topic from the transcript.
        Focus on:
        - Specific details, numbers, and dates mentioned
        - Key decisions or conclusions
        - Actions or next steps related to this topic
        
        Topic: {topic['title']}
        Relevant Context: {topic['context']}
        """
        
        try:
            response = self.client.chat.completions.create(
                model=self.main_model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.5,
                max_tokens=1000
            )
            
            return response.choices[0].message.content
        except Exception as e:
            st.error(f"Error generating detailed summary: {str(e)}")
            return ""

    def validate_coverage(self, transcript: str, summaries: Dict[str, str]) -> List[str]:
        """Third pass: Validate coverage and identify any missed topics"""
        prompt = f"""
        Review these summaries and the original transcript. Identify any significant topics
        or details that might have been missed. Focus on:
        - Important topics not covered in the summaries
        - Significant details that were overlooked
        - Any inconsistencies between the transcript and summaries

        Summaries:
        {json.dumps(summaries, indent=2)}

        Original Transcript:
        {transcript}

        Return your findings as a JSON array of strings.
        """
        
        try:
            response = self.client.chat.completions.create(
                model=self.mini_model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                response_format={ "type": "json_object" }
            )
            
            return json.loads(response.choices[0].message.content)["missed_topics"]
        except Exception as e:
            st.error(f"Error validating coverage: {str(e)}")
            return []

    def process_transcript(self, transcript: str) -> str:
        """Main pipeline for processing longer transcripts"""
        # Step 1: Extract topics
        topics = self.extract_topics(transcript)
        
        # Step 2: Generate detailed summaries for each topic
        detailed_summaries = {}
        for topic in topics:
            detailed_summaries[topic['title']] = self.generate_detailed_summary(topic)
        
        # Step 3: Validate coverage
        missed_topics = self.validate_coverage(transcript, detailed_summaries)
        
        # Step 4: Combine everything into a final summary
        final_summary = "# Detailed Summary\n\n"
        
        for topic_title, summary in detailed_summaries.items():
            final_summary += f"## {topic_title}\n{summary}\n\n"
        
        if missed_topics:
            final_summary += "\n## Additional Notes\n"
            for topic in missed_topics:
                final_summary += f"- {topic}\n"
        
        # Add disclaimer if there are failed chunks
        if "Een deel van de transcriptie is gefaald" in transcript:
            disclaimer = (
                "\n\n**Let op:** Een deel van de transcriptie is gefaald. "
                "De nauwkeurigheid van de samenvatting kan hierdoor minder zijn "
                "of er kunnen onderdelen ontbreken."
            )
            final_summary += disclaimer

        return final_summary

def generate_enhanced_summary(transcript: str, client: OpenAI) -> str:
    """Helper function to generate enhanced summary"""
    pipeline = EnhancedSummaryPipeline(client)
    return pipeline.process_transcript(transcript)
