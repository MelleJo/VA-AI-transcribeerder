import os
from typing import Dict

PROMPTS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "prompts")

def load_prompts() -> Dict[str, str]:
    """Load all prompt files"""
    prompts = {}
    
    # Load base prompt
    base_prompt_path = os.path.join(PROMPTS_DIR, 'base_prompt.txt')
    try:
        with open(base_prompt_path, 'r', encoding='utf-8') as f:
            prompts['base_prompt'] = f.read()
    except FileNotFoundError:
        print(f"Base prompt file not found: {base_prompt_path}")
    
    # Load other prompts
    for filename in os.listdir(PROMPTS_DIR):
        if filename.endswith('.txt') and filename != 'base_prompt.txt':
            prompt_name = os.path.splitext(filename)[0]
            file_path = os.path.join(PROMPTS_DIR, filename)
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    prompts[prompt_name] = f.read()
            except FileNotFoundError:
                print(f"Prompt file not found: {file_path}")
    
    return prompts

def get_prompt_content(prompt_name: str) -> str:
    """Get content of a specific prompt"""
    file_path = os.path.join(PROMPTS_DIR, f"{prompt_name}.txt")
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        return ""