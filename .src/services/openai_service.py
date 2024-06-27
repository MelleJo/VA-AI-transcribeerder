from openai import OpenAI

client = None

def initialize_openai_client(api_key):
    global client
    client = OpenAI(api_key=api_key)

def get_openai_client():
    global client
    if client is None:
        raise ValueError("OpenAI client is not initialized. Call initialize_openai_client first.")
    return client