from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from config import LLM_MODEL

llm = ChatOpenAI(model=LLM_MODEL, temperature=0.2)

def generate_insights(state):
    context = "\n\n".join([c["text"][:500] for c in state["chunks"][:15]])
    prompt = ChatPromptTemplate.from_template(
        """You are the BEST research paper insight generator.

Paper: {title}

Context:
{context}

Provide deep, high-value insights:
• Core novelty and contribution
• Why this paper matters (impact)
• Strengths of the approach
• Potential future research directions
• Real-world applications
• How it advances the field

Be critical, insightful, and professional."""
    )
    chain = prompt | llm
    state["insights"] = chain.invoke({
        "title": state["paper"].title,
        "context": context
    }).content
    return state