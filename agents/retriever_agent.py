from embedding.embedder import ChunkingEmbedder
from vectorstore.faiss_store import VectorMemory
import logging

logger = logging.getLogger(__name__)
embedder = ChunkingEmbedder()

def retrieve(state):
    """Fixed retriever - uses user_instruction instead of old 'query'"""
    # Use chunks passed from main app
    chunks = state.get("chunks", [])
    
    if chunks:
        logger.info(f"✅ Using {len(chunks)} chunks from state")
        # If chunks are provided, return them as-is or rank by similarity
        query_text = state.get("user_instruction", "Summarize this research paper")
        
        try:
            q_emb = embedder.embedder.encode(query_text, normalize_embeddings=True)
            
            # Rank chunks by similarity if they have embeddings
            if chunks and isinstance(chunks[0], dict) and "embedding" in chunks[0]:
                import numpy as np
                chunk_embs = np.array([c.get("embedding", []) for c in chunks], dtype="float32")
                similarities = np.dot(chunk_embs, q_emb)
                ranked_indices = np.argsort(similarities)[::-1][:12]
                state["chunks"] = [chunks[i] for i in ranked_indices]
            else:
                state["chunks"] = chunks[:12]
        except Exception as e:
            logger.warning(f"Could not rank chunks: {e}, using as-is")
            state["chunks"] = chunks[:12]
    else:
        logger.warning("No chunks provided in state, using empty list")
        state["chunks"] = []
    
    return state