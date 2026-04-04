"""
Rode esse script para ver quais modelos estão disponíveis na sua API key.
"""
import os
from dotenv import load_dotenv
from google import genai

load_dotenv()

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

print("Modelos disponíveis:\n")
for model in client.models.list():
    print(f"  {model.name}")
