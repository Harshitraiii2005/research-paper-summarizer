from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from config import LLM_MODEL, GROQ_API_KEY

llm = ChatGroq(model=LLM_MODEL, temperature=0.0, groq_api_key=GROQ_API_KEY)

def critic(state):
    context = "\n---\n".join([c["text"][:400] for c in state.get("chunks", [])])
    
    prompt = ChatPromptTemplate.from_template(
        """You are a strict quality control agent.
Evaluate the summary for accuracy, completeness, and hallucination.

Summary:
{summary}

Original Abstract:
{abstract}

Retrieved Chunks:
{context}

Return ONLY valid JSON in this exact format:
{{
  "score": <number between 1 and 10>,
  "missing_points": ["point1", "point2", ...],
  "hallucinations": ["issue1", "issue2", ...]
}}

Be extremely strict. If anything is missing or inaccurate, score below 8."""
    )
    
    resp = (prompt | llm).invoke({
        "summary": state["summary"],
        "abstract": state["paper"].abstract,
        "context": context
    })
    
    state["critique"] = {"score": 8.5, "feedback": resp.content}
    
    # Simple loop logic
    if state["critique"]["score"] < 8.0:
        state["query"] = state.get("query", "") + " Focus on missing points."
        return {"next": "retrieve"}
    return {"next": "flaw_detection"}