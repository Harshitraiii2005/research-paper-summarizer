import os
from dotenv import load_dotenv

load_dotenv()

# ====================== API KEYS ======================
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")   # Keep for future use if needed
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

if not GROQ_API_KEY:
    raise ValueError("❌ GROQ_API_KEY is missing! Please add it to your .env file.")

# ====================== MODELS ======================
LLM_MODEL = "llama-3.3-70b-versatile"   # Excellent free model on Groq

EMBEDDING_MODEL = "allenai/scibert_scivocab_uncased"

# ====================== OTHER SETTINGS ======================
GROBID_URL = os.getenv("GROBID_URL", "http://localhost:8070")
DB_PATH = "paper_agent.db"

# ====================== CONFIG CONFIRMATION ======================
print("✅ Config loaded successfully")
print(f"   LLM Model      : {LLM_MODEL} (Groq)")
print(f"   Embedding Model: {EMBEDDING_MODEL}")
print(f"   GROBID URL     : {GROBID_URL}")