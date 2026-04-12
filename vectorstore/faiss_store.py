import faiss
import numpy as np
import pickle
from pathlib import Path

class VectorMemory:
    def __init__(self, dim: int = 768):
        self.index = faiss.IndexFlatIP(dim)
        self.chunks: list = []
    
    def add(self, chunks: list[dict]):
        if not chunks: return
        embs = np.array([c["embedding"] for c in chunks], dtype="float32")
        self.index.add(embs)
        self.chunks.extend(chunks)
        print(f"✅ Stored {len(chunks)} chunks in FAISS")
    
    def retrieve(self, query_embedding: list, k: int = 10) -> list[dict]:
        if not self.chunks: return []
        q = np.array([query_embedding], dtype="float32")
        _, indices = self.index.search(q, min(k, len(self.chunks)))
        return [self.chunks[int(i)] for i in indices[0]]