from langgraph.graph import StateGraph, END
from typing import TypedDict
import logging
import time

logger = logging.getLogger(__name__)

from agents.retriever_agent import retrieve
from agents.summarizer_agent import summarize
from agents.critic_agent import critic
from agents.insight_agent import generate_insights
from agents.flaw_detector_agent import detect_flaws
from agents.context_agent import add_context
from agents.qa_agent import answer_general_question
from agents.personalization_agent import personalize
from agents.router_agent import route_user_instruction


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
    ppt_outline: str
    application: str
    mode: str
    final_output: str
    ppt_file: str


def timed_node(name, func):
    """Wrapper to time each node"""
    def wrapper(state: AgentState):
        start = time.time()
        logger.info(f"🔄 Starting node: {name}")
        try:
            result = func(state)
            elapsed = time.time() - start
            logger.info(f"✅ Completed node {name} in {elapsed:.2f}s")
            return result
        except Exception as e:
            elapsed = time.time() - start
            logger.error(f"❌ Node {name} failed after {elapsed:.2f}s: {str(e)}")
            raise
    return wrapper


def router_node(state: AgentState):
    state["router_decision"] = route_user_instruction(state["user_instruction"])
    state["mode"] = state["router_decision"].get("mode", "researcher")
    return state


def decide_after_retrieve(state: AgentState):
    """Decide next step after retrieval based on router decision"""
    tasks = state["router_decision"].get("tasks", [])
    if "qa" in tasks:
        return "qa"
    return "summarize"


workflow = StateGraph(AgentState)

workflow.add_node("router", timed_node("router", router_node))
workflow.add_node("retrieve", timed_node("retrieve", retrieve))
workflow.add_node("summarize", timed_node("summarize", summarize))
workflow.add_node("insights", timed_node("insights", generate_insights))
workflow.add_node("flaw_detection", timed_node("flaw_detection", detect_flaws))
workflow.add_node("context", timed_node("context", add_context))
workflow.add_node("qa", timed_node("qa", answer_general_question))
workflow.add_node("personalize", timed_node("personalize", personalize))
workflow.add_node("ppt", timed_node("ppt", generate_ppt_agent))
workflow.add_node("application", timed_node("application", generate_application))

workflow.set_entry_point("router")
workflow.add_edge("router", "retrieve")


workflow.add_conditional_edges(
    "retrieve",
    decide_after_retrieve,
    {
        "qa": "qa",
        "summarize": "summarize"
    }
)


workflow.add_edge("summarize", "insights")
workflow.add_edge("insights", "flaw_detection")
workflow.add_edge("flaw_detection", "context")
workflow.add_edge("context", "personalize")
workflow.add_edge("qa", "personalize")


workflow.add_edge("personalize", "ppt")
workflow.add_edge("ppt", "application")
workflow.add_edge("application", END)

paper_graph = workflow.compile()