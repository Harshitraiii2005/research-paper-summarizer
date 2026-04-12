import fitz
import pymupdf4llm
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from knowledge.schema import PaperKnowledge
from config import LLM_MODEL
from ingestion.grobid_parser import parse_with_grobid

class IngestionAgent:
    def __init__(self, use_grobid: bool = True):
        self.llm = ChatOpenAI(model=LLM_MODEL, temperature=0.1)
        self.use_grobid = use_grobid
    
    def ingest(self, pdf_path: str) -> PaperKnowledge:
        if self.use_grobid:
            try:
                return parse_with_grobid(pdf_path)
            except:
                print("⚠️ GROBID unavailable – using fallback")
        
        # Fallback PyMuPDF + LLM
        md_text = pymupdf4llm.to_markdown(pdf_path)
        prompt = ChatPromptTemplate.from_template(
            "Parse this paper into exact PaperKnowledge JSON:\n{content}"
        )
        chain = prompt | self.llm.with_structured_output(PaperKnowledge)
        knowledge: PaperKnowledge = chain.invoke({"content": md_text[:18000]})
        knowledge.metadata["source"] = pdf_path
        print(f"✅ Ingested: {knowledge.title}")
        return knowledge