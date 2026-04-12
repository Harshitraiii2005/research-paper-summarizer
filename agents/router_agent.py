from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from config import LLM_MODEL

llm = ChatOpenAI(model=LLM_MODEL, temperature=0.1)

router_prompt = ChatPromptTemplate.from_template(
    """You are the smartest router for the BEST research paper AI assistant.

User request: {user_input}

Decide exactly what the user wants. Return ONLY valid JSON with these keys:

{{
  "mode": "beginner" | "researcher" | "interview",
  "tasks": ["summarize", "insights", "flaw_detection", "comparison", "ppt", "qa", "explain_like_10", "interview_qa", "custom"],
  "custom_instructions": "any extra detail the user wants"
}}

Rules:
- Always include "summarize" + "insights" unless user says otherwise.
- Use "qa" for any general question about the paper.
- Use "insights" for deep analysis, novelty, impact, future work.
- Use "ppt" only if user explicitly wants slides.
- Be precise. You can combine multiple tasks.

Example:
{{"mode": "researcher", "tasks": ["summarize", "insights", "flaw_detection"], "custom_instructions": "focus on limitations and real-world impact"}}
"""
)

def route_user_instruction(user_input: str) -> dict:
    chain = router_prompt | llm
    response = chain.invoke({"user_input": user_input})
    try:
        import json
        decision = json.loads(response.content)
        # Ensure minimum quality
        if "summarize" not in decision["tasks"] and "insights" not in decision["tasks"] and "qa" not in decision["tasks"]:
            decision["tasks"].insert(0, "summarize")
        return decision
    except:
        return {"mode": "researcher", "tasks": ["summarize", "insights"], "custom_instructions": ""}