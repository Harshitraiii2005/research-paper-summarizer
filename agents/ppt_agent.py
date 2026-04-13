from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from config import LLM_MODEL, GROQ_API_KEY
from output.ppt_generator import generate_ppt

llm = ChatGroq(model=LLM_MODEL, temperature=0.3, groq_api_key=GROQ_API_KEY)

def generate_ppt_agent(state):
    """PPT Agent: Creates a professional presentation outline"""
    prompt = ChatPromptTemplate.from_template(
        """Create a professional 10-12 slide PowerPoint presentation for this research paper.
Make it suitable for a medical conference or academic presentation.

Paper Title: {title}

Summary: {summary}
Key Insights: {insights}
Flaws & Limitations: {flaws}

For each slide, provide:
- Slide Title
- 3-5 key bullet points
- Suggestion for visual (e.g., figure, diagram, table)

Focus on clarity, visual appeal, and key takeaways."""
    )

    chain = prompt | llm
    response = chain.invoke({
        "title": state["paper"].title,
        "summary": state.get("summary", ""),
        "insights": state.get("insights", ""),
        "flaws": state.get("flaws", "")
    })

    state["ppt_outline"] = response.content

    # Optional: Auto-generate actual PPT file
    try:
        ppt_file = generate_ppt(
            paper=state["paper"],
            summary=state.get("summary", ""),
            flaws=state.get("flaws", ""),
            comparison=state.get("comparison", ""),
            user_id=state.get("user_id")  # if you pass user_id
        )
        state["ppt_file"] = ppt_file
    except:
        state["ppt_file"] = None

    return state