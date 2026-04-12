from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from config import LLM_MODEL

llm = ChatOpenAI(model=LLM_MODEL, temperature=0.3)

def summarize(state):
    context = "\n\n".join([c["text"] for c in state["chunks"]])
    custom = state["router_decision"].get("custom_instructions", "")
    
    prompt = ChatPromptTemplate.from_template(
        """You are the BEST research paper summarizer.

Paper: {title}

Context:
{context}

User wants: {custom}

Create an outstanding structured summary with:
• Key Contributions
• Methodology Overview
• Main Results
• Limitations (brief)

Make it clear, insightful, and professional."""
    )
    chain = prompt | llm
    state["summary"] = chain.invoke({
        "title": state["paper"].title,
        "context": context,
        "custom": custom
    }).content
    return state