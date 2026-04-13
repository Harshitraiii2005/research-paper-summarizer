from langgraph.graph import StateGraph, END
from typing import TypedDict

# Import all agents
from agents.retriever_agent import retrieve
from agents.summarizer_agent import summarize
from agents.critic_agent import critic
from agents.insight_agent import generate_insights
from agents.flaw_detector_agent import detect_flaws
from agents.context_agent import add_context
from agents.qa_agent import answer_general_question
from agents.personalization_agent import personalize
from agents.router_agent import route_user_instruction

# NEW AGENTS
from agents.ppt_agent import generate_ppt_agent
from agents.application_agent import generate_application

from knowledge.schema import PaperKnowledge


class AgentState(TypedDict):
    paper: PaperKnowledge
    user_instruction: str
    router_decision: dict
    chunks: list
    summary: str
    insights: str
    flaws: str
    comparison: str
    qa_answer: str
    ppt_outline: str          # New
    application: str          # New
    mode: str
    final_output: str
    ppt_file: str


def router_node(state: AgentState):
    state["router_decision"] = route_user_instruction(state["user_instruction"])
    state["mode"] = state["router_decision"].get("mode", "researcher")
    return state


def decide_after_retrieve(state: AgentState):
    tasks = state["router_decision"].get("tasks", [])
    if "qa" in tasks:
        return "qa"
    return "summarize"


workflow = StateGraph(AgentState)

workflow.add_node("router", router_node)
workflow.add_node("retrieve", retrieve)
workflow.add_node("summarize", summarize)
workflow.add_node("insights", generate_insights)
workflow.add_node("flaw_detection", detect_flaws)
workflow.add_node("context", add_context)
workflow.add_node("qa", answer_general_question)
workflow.add_node("personalize", personalize)

# NEW NODES
workflow.add_node("ppt", generate_ppt_agent)
workflow.add_node("application", generate_application)

workflow.set_entry_point("router")
workflow.add_edge("router", "retrieve")
workflow.add_conditional_edges("retrieve", decide_after_retrieve)

workflow.add_edge("summarize", "insights")
workflow.add_edge("insights", "flaw_detection")
workflow.add_edge("flaw_detection", "context")
workflow.add_edge("context", "personalize")
workflow.add_edge("qa", "personalize")

# NEW EDGES - after personalization
workflow.add_edge("personalize", "ppt")
workflow.add_edge("personalize", "application")
workflow.add_edge("ppt", END)
workflow.add_edge("application", END)

paper_graph = workflow.compile()