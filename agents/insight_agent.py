from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from config import LLM_MODEL, GROQ_API_KEY

llm = ChatGroq(model=LLM_MODEL, temperature=0.2, groq_api_key=GROQ_API_KEY)

def generate_insights(state):
    context = "\n\n".join([c["text"][:500] for c in state["chunks"][:15]])

    prompt = ChatPromptTemplate.from_template(
        """You are an elite research insight generator.

Paper Title: {title}

Context:
{context}

Provide deep, high-value academic insights. Be critical and insightful.
Cover:
• Core novelty and scientific contribution
• Why this paper is important (real impact)
• Major strengths of the work
• Weaknesses or gaps
• Promising future research directions
• Real-world applications and implications

Use professional academic tone. Be specific and thoughtful."""
    )

    chain = prompt | llm
    state["insights"] = chain.invoke({
        "title": state["paper"].title,
        "context": context
    }).content
    return state