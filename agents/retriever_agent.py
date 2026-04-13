from embedding.embedder import ChunkingEmbedder
from vectorstore.faiss_store import VectorMemory

embedder = ChunkingEmbedder()
memory = VectorMemory()

def retrieve(state):
    """Fixed retriever - uses user_instruction instead of old 'query'"""
    # Use the natural language instruction from the user
    query_text = state.get("user_instruction", "")
    
    # Fallback if empty
    if not query_text and state.get("summary"):
        query_text = state["summary"]
    if not query_text:
        query_text = "Summarize this research paper"

    q_emb = embedder.embedder.encode(query_text, normalize_embeddings=True).tolist()
    state["chunks"] = memory.retrieve(q_emb, k=12)
    return state