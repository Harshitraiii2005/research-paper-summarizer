from ingestion.pdf_ingestor import IngestionAgent
from embedding.embedder import ChunkingEmbedder
from vectorstore.faiss_store import VectorMemory
from utils.arxiv_downloader import download_arxiv_paper
from graph.agent_graph import paper_graph
from output.ppt_generator import generate_ppt
from database import save_paper, init_db
import sys
from knowledge.schema import PaperKnowledge

init_db()

def main():
    print("🧠 Best Research Paper AI Assistant (Summarizer + Insights + Any Task)\n")
    
    # Input
    user_input = input("Enter PDF path or arXiv ID/URL: ").strip()
    if "arxiv" in user_input.lower() or any(c.isdigit() for c in user_input.replace(".", "")):
        pdf_path = download_arxiv_paper(user_input)
    else:
        pdf_path = user_input

    # Process paper
    ingestor = IngestionAgent(use_grobid=True)
    embedder = ChunkingEmbedder()
    memory = VectorMemory()

    print("📥 Ingesting paper with GROBID...")
    paper: PaperKnowledge = ingestor.ingest(pdf_path)

    print("🔍 Creating semantic chunks...")
    chunks = embedder.chunk_and_embed(paper)
    memory.add(chunks)

    # User can give any instruction
    print("\n💬 You can now tell me anything (e.g. 'Give best summary with insights', 'Find all flaws', 'Make PPT', 'Explain like 10')")
    user_instruction = input("Your request: ").strip()
    if not user_instruction:
        user_instruction = "Give the best structured summary with deep insights and key limitations"

    print("\n🚀 Running smart agent pipeline...\n")
    
    result = paper_graph.invoke({
        "paper": paper,
        "user_instruction": user_instruction,
        "chunks": [],
        "summary": "",
        "insights": "",
        "flaws": "",
        "comparison": "",
        "qa_answer": "",
        "mode": "researcher",
        "final_output": "",
        "ppt_file": ""
    })

    # Generate PPT if requested
    if "ppt" in result.get("router_decision", {}).get("tasks", []):
        ppt_file = generate_ppt(
            paper,
            result.get("summary", ""),
            result.get("flaws", ""),
            result.get("comparison", ""),
            user_id=None  # CLI doesn't have user_id
        )
        result["ppt_file"] = ppt_file
        print(f"📊 PPT generated: {ppt_file}")

    print("=" * 100)
    print("FINAL OUTPUT")
    print("=" * 100)
    print(result.get("final_output", result.get("summary", "No output generated")))

    
    print("\n✅ Done! (CLI version does not save to 10-day memory)")

if __name__ == "__main__":
    main()