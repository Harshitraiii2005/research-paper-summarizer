import arxiv
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from config import LLM_MODEL

llm = ChatOpenAI(model=LLM_MODEL, temperature=0.3)

def add_context(state):
    # Search similar papers
    query = state["paper"].title + " " + state["paper"].abstract[:200]
    search = arxiv.Search(query=query, max_results=3, sort_by=arxiv.SortCriterion.Relevance)
    similar = list(search.results())
    
    comp_text = "Similar papers:\n"
    for p in similar:
        comp_text += f"• {p.title} ({p.published.year}) - {p.summary[:150]}...\n"
    
    prompt = ChatPromptTemplate.from_template(
        "Compare this paper with the 3 similar ones:\n{comp_text}\n\nPaper summary: {summary}"
    )
    state["comparison"] = (prompt | llm).invoke({"comp_text": comp_text, "summary": state["summary"]}).content
    return state