from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from config import LLM_MODEL, GROQ_API_KEY

llm = ChatGroq(model=LLM_MODEL, temperature=0.3, groq_api_key=GROQ_API_KEY)

def generate_application(state):
    """Application Agent: Translates research into practical, actionable advice"""
    prompt = ChatPromptTemplate.from_template(
        """You are an expert in translating research papers into real-world practice.

Paper Title: {title}

Summary: {summary}
Key Insights: {insights}

Provide clear, actionable recommendations for the following groups:

1. **Clinicians / Neurologists** – What should they do differently in practice?
2. **Pharmacists** – Key points on medication management and patient counseling.
3. **Researchers** – What are the most promising next research steps?
4. **Patients & Caregivers** – Practical advice they can understand and apply.

Be specific, evidence-based, and practical. Focus on real-world impact."""
    )

    chain = prompt | llm
    state["application"] = chain.invoke({
        "title": state["paper"].title,
        "summary": state.get("summary", ""),
        "insights": state.get("insights", "")
    }).content

    return state