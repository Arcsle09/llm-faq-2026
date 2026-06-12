import anthropic
from openai import OpenAI
import os
from dotenv import load_dotenv
load_dotenv()

def instantiate_anthropic_client():
    client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    return client



def instantiate_openai_client():
    client = OpenAI()
    return client