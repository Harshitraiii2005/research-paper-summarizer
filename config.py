import os
from dotenv import load_dotenv

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Use a much cheaper model or switch to Groq (free tier available)
LLM_MODEL = "gpt-4o-mini"          # still cheap, but you hit quota

# Temporary workaround: Use Groq (very fast + generous free tier)
# LLM_MODEL = "llama3-70b-8192"     # Uncomment if you add Groq key

EMBEDDING_MODEL = "allenai/scibert_scivocab_uncased"
GROBID_URL = os.getenv("GROBID_URL", "http://localhost:8070")
DB_PATH = "paper_agent.db"

print("✅ Config loaded")