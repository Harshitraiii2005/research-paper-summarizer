from sentence_transformers import SentenceTransformer
from langchain_text_splitters import RecursiveCharacterTextSplitter
from knowledge.schema import PaperKnowledge

class ChunkingEmbedder:
    def __init__(self):
        self.embedder = SentenceTransformer("allenai/scibert_scivocab_uncased")

    def chunk_and_embed(self, paper: PaperKnowledge) -> list[dict]:
        chunks = []
        splitter = RecursiveCharacterTextSplitter(chunk_size=750, chunk_overlap=100)

        for sec_name, content in paper.sections.items():
            for chunk_text in splitter.split_text(content):
                chunks.append({
                    "text": f"Section: {sec_name.upper()}\n{chunk_text}",
                    "metadata": {"section": sec_name, "title": paper.title, "type": "text"}
                })

        if paper.abstract:
            chunks.append({"text": f"Abstract: {paper.abstract}", "metadata": {"section": "abstract", "type": "text"}})

        for fig in paper.figures:
            chunks.append({"text": f"Figure (Page {fig.page}): {fig.caption}", "metadata": {"type": "figure", "page": fig.page}})

        for tbl in paper.tables:
            chunks.append({"text": f"Table (Page {tbl.page}): {tbl.caption}", "metadata": {"type": "table", "page": tbl.page}})

        texts = [c["text"] for c in chunks]
        embeddings = self.embedder.encode(texts, normalize_embeddings=True)
        for i, emb in enumerate(embeddings):
            chunks[i]["embedding"] = emb.tolist()

        print(f"✅ Created {len(chunks)} semantic chunks")
        return chunks