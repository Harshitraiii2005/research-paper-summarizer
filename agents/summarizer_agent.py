from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from config import LLM_MODEL, GROQ_API_KEY

llm = ChatGroq(model=LLM_MODEL, temperature=0.3, groq_api_key=GROQ_API_KEY)

def summarize(state):
    context = "\n\n".join([c["text"] for c in state["chunks"]])
    custom = state["router_decision"].get("custom_instructions", "")
    
    prompt = ChatPromptTemplate.from_template(
        """You are the world's best research paper summarizer.
Write a clear, accurate, and professional summary.

Paper Title: {title}

Context:
{context}

User Instructions: {custom}

Structure your summary strictly with these sections:
• **Key Contributions** (What is new?)
• **Methodology Overview** (High-level, clear)
• **Main Results** (Most important findings)
• **Limitations** (Be honest)

Be concise, factual, and insightful. Never hallucinate."""
    )
    
    chain = prompt | llm
    state["summary"] = chain.invoke({
        "title": state["paper"].title,
        "context": context,
        "custom": custom
    }).content
    return state