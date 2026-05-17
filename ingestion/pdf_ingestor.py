import fitz
import pymupdf4llm
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from knowledge.schema import PaperKnowledge
from config import LLM_MODEL, GROQ_API_KEY

class IngestionAgent:
    def __init__(self, use_grobid: bool = True):

        self.llm = ChatGroq(
            model=LLM_MODEL,
            temperature=0.1,
            groq_api_key=GROQ_API_KEY
        )
        self.use_grobid = use_grobid

    def ingest(self, pdf_path: str) -> PaperKnowledge:
        if self.use_grobid:
            try:
                from ingestion.grobid_parser import parse_with_grobid
                return parse_with_grobid(pdf_path)
            except Exception as e:
                print(f"⚠️ GROBID failed ({e}). Using fallback parser.")


        md_text = pymupdf4llm.to_markdown(pdf_path)

        prompt = ChatPromptTemplate.from_template(
            """You are an expert research paper parser.
Extract the following information accurately and return ONLY valid JSON matching the PaperKnowledge schema.

Paper content:
{content}

Be precise with title, authors, abstract, and section names."""
        )

        chain = prompt | self.llm.with_structured_output(PaperKnowledge)
        knowledge: PaperKnowledge = chain.invoke({"content": md_text[:18000]})
        knowledge.metadata["source"] = pdf_path
        print(f"✅ Ingested paper: {knowledge.title}")
        return knowledge
