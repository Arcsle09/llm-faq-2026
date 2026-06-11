from dotenv import load_dotenv
import anthropic
import os

def instantiate_anthropic_client():
    load_dotenv()
    client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    return client



