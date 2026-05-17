import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
from graph.agent_graph import paper_graph
from knowledge.schema import PaperKnowledge


test_paper = PaperKnowledge(
    title="Review of the Epilepsy, Including Its Causes, Symptoms, Biomarkers, and Management",
    authors=["Yash Srivastav", "Akhandnath Prajapati", "Prachi Agrahari", "Madhaw Kumar"],
    abstract="Epilepsy is a long-term medical disorder that frequently causes unpredictable, unprovoked repeated seizures...",
    sections={
        "introduction": "Introduction content here...",
        "causes": "Causes content here...",
        "management": "Management content here..."
    },
    figures=[],
    tables=[],
    metadata={"year": 2023, "doi": "10.9734/AJRIMPS/2023/v12i4232"}
)


def test_full_pipeline():
    """Test the complete agentic pipeline"""
    input_state = {
        "paper": test_paper,
        "user_instruction": "Give best summary with insights and flaws",
        "chunks": [],
        "summary": "",
        "insights": "",
        "flaws": "",
        "comparison": "",
        "qa_answer": "",
        "ppt_outline": "",
        "application": "",
        "mode": "researcher",
        "final_output": "",
        "ppt_file": ""
    }

    result = paper_graph.invoke(input_state)

    assert isinstance(result, dict)
    assert "summary" in result and result["summary"]
    assert "insights" in result and result["insights"]
    assert "flaws" in result


def test_qa_routing():
    """Test QA mode routing"""
    input_state = {
        "paper": test_paper,
        "user_instruction": "What are the main symptoms of epilepsy?",
        "chunks": [],
        "summary": "",
        "insights": "",
        "flaws": "",
        "comparison": "",
        "qa_answer": "",
        "ppt_outline": "",
        "application": "",
        "mode": "researcher",
        "final_output": "",
        "ppt_file": ""
    }

    result = paper_graph.invoke(input_state)
    assert "qa_answer" in result and result["qa_answer"]


def test_ppt_and_application():
    """Test PPT and Application agents"""
    input_state = {
        "paper": test_paper,
        "user_instruction": "Make a PPT and give real-world clinical applications",
        "chunks": [],
        "summary": "",
        "insights": "",
        "flaws": "",
        "comparison": "",
        "qa_answer": "",
        "ppt_outline": "",
        "application": "",
        "mode": "researcher",
        "final_output": "",
        "ppt_file": ""
    }

    result = paper_graph.invoke(input_state)
    assert "ppt_outline" in result
    assert "application" in result