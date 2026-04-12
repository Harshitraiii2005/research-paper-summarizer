from embedding.embedder import ChunkingEmbedder
from vectorstore.faiss_store import VectorMemory

embedder = ChunkingEmbedder()
memory = VectorMemory()

def retrieve(state):
    query = state["query"]
    q_emb = embedder.embedder.encode(query, normalize_embeddings=True).tolist()
    state["chunks"] = memory.retrieve(q_emb, k=12)
    return state