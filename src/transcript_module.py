import streamlit as st

def render_transcript_edit(input_text):
    """
    Render the transcript editing interface.
    
    Args:
        input_text (str): The initial transcript text.
    
    Returns:
        str: The edited transcript text.
    """
    st.subheader("Stap 3: Transcript bewerken")
    
    if not input_text:
        st.warning("Er is geen transcript om te bewerken. Ga terug naar de vorige stap om tekst in te voeren.")
        return None
    
    edited_text = st.text_area("Bewerk het transcript indien nodig:", value=input_text, height=400)
    
    if st.button("Bevestig transcript"):
        if edited_text:
            st.success("Transcript bevestigd.")
            return edited_text
        else:
            st.warning("Het transcript mag niet leeg zijn.")
            return None
    
    return None

def confirm_transcript(transcript):
    """
    Confirm the final transcript.
    
    Args:
        transcript (str): The transcript to confirm.
    
    Returns:
        bool: True if confirmed, False otherwise.
    """
    st.subheader("Bevestig het transcript")
    st.write(transcript)
    
    if st.button("Bevestig en ga door naar samenvatting"):
        return True
    
    return False