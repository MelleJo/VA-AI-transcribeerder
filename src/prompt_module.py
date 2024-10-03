import os
import streamlit as st

PROMPTS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "prompts")

def get_prompt_names():
    """
    Retrieves a list of available prompt names, excluding the base prompt.
    
    Returns:
        list: A list of prompt names (without file extensions).
    """
    prompts = [f for f in os.listdir(PROMPTS_DIR) if f.endswith('.txt') and f != 'base_prompt.txt']
    return [os.path.splitext(f)[0] for f in prompts]

def get_prompt_content(prompt_name):
    """
    Retrieves the content of a specific prompt file.
    
    Args:
        prompt_name (str): The name of the prompt (without file extension).
    
    Returns:
        str: The content of the prompt file.
    """
    file_path = os.path.join(PROMPTS_DIR, f"{prompt_name}.txt")
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        st.error(f"Prompt file not found: {file_path}")
        return ""

def load_base_prompt():
    """
    Loads the content of the base prompt file.
    
    Returns:
        str: The content of the base prompt file.
    """
    base_prompt_path = os.path.join(PROMPTS_DIR, 'base_prompt.txt')
    try:
        with open(base_prompt_path, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        st.error(f"Base prompt file not found: {base_prompt_path}")
        return ""

def render_prompt_selection():
    """
    Renders the prompt selection interface.
    
    Returns:
        str: The selected prompt name.
    """
    st.subheader("Selecteer een prompt")
    prompts = get_prompt_names()
    selected_prompt = st.selectbox("Kies een instructieset:", prompts)
    return selected_prompt