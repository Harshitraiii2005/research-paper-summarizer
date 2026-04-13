from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from config import LLM_MODEL, GROQ_API_KEY

llm = ChatGroq(model=LLM_MODEL, temperature=0.1, groq_api_key=GROQ_API_KEY)

router_prompt = ChatPromptTemplate.from_template(
    """You are the smartest routing agent for a research paper intelligence system.

User request: {user_input}

Return **ONLY** valid JSON with these exact keys:

{{
  "mode": "beginner" | "researcher" | "interview",
  "tasks": ["summarize", "insights", "flaw_detection", "comparison", "ppt", "qa", "explain_like_10", "interview_qa", "application", "custom"],
  "custom_instructions": "any specific user request"
}}

Rules:
- Always include "summarize" and "insights" unless user explicitly asks for something else.
- Use "ppt" when user wants a PowerPoint presentation or slides.
- Use "application" when user wants practical, real-world recommendations for clinicians, pharmacists, researchers, or patients.
- Use "qa" for any direct question about the paper.
- Be precise and intelligent.

Return nothing except the JSON object."""
)

def route_user_instruction(user_input: str) -> dict:
    chain = router_prompt | llm
    response = chain.invoke({"user_input": user_input})
    try:
        import json
        decision = json.loads(response.content)
        return decision
    except:
        return {
            "mode": "researcher",
            "tasks": ["summarize", "insights", "application"],
            "custom_instructions": ""
        }