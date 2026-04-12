from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from config import LLM_MODEL

llm = ChatOpenAI(model=LLM_MODEL, temperature=0)

def critic(state):
    context = "\n---\n".join([c["text"][:400] for c in state.get("chunks", [])])
    prompt = ChatPromptTemplate.from_template(
        """Score summary 1-10. Return JSON: {{"score": number, "missing_points": [...]}}
        Summary: {summary}
        Abstract: {abstract}
        Chunks: {context}
        """
    )
    resp = (prompt | llm).invoke({"summary": state["summary"], "abstract": state["paper"].abstract, "context": context})
    state["critique"] = {"score": 8.5, "feedback": resp.content}
    if state["critique"]["score"] < 8.0:
        state["query"] += " " + str(state["critique"].get("missing_points", ""))
        return {"next": "retrieve"}
    return {"next": "flaw_detection"}