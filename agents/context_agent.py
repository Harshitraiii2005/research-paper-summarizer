import arxiv
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from config import LLM_MODEL, GROQ_API_KEY
from dotenv import load_dotenv

load_dotenv()

llm = ChatGroq(
    model=LLM_MODEL,
    temperature=0.3,
    groq_api_key=GROQ_API_KEY
)

def add_context(state):
    """Context Agent: Find and compare with 3 similar papers"""
    try:
        query = state["paper"].title + " " + (state["paper"].abstract[:300] if state["paper"].abstract else "")
        
        # FIXED: Use new recommended way (Client.results)
        client = arxiv.Client()
        search = arxiv.Search(
            query=query,
            max_results=3,
            sort_by=arxiv.SortCriterion.Relevance
        )
        similar_papers = list(client.results(search))

        comp_text = "Similar papers found on arXiv:\n\n"
        for p in similar_papers:
            year = p.published.year if p.published else "N/A"
            comp_text += f"• **{p.title}** ({year})\n"
            comp_text += f"  {p.summary[:180]}...\n\n"

        prompt = ChatPromptTemplate.from_template(
            """Compare the main paper with the following 3 similar papers.
Focus on differences in methodology, contributions, strengths, and limitations.

Main Paper Title: {title}

Similar Papers:
{comp_text}

Main Paper Summary:
{summary}

Provide a clear, insightful comparison."""
        )

        response = (prompt | llm).invoke({
            "title": state["paper"].title,
            "comp_text": comp_text,
            "summary": state.get("summary", "No summary available yet.")
        })

        state["comparison"] = response.content

    except Exception as e:
        print(f"⚠️ Context Agent warning: {e}")
        state["comparison"] = "Could not fetch similar papers at this time."

    return state