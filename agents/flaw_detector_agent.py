from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from config import LLM_MODEL

llm = ChatOpenAI(model=LLM_MODEL, temperature=0.2)

def detect_flaws(state):
    prompt = ChatPromptTemplate.from_template(
        """Analyze methodology & results for flaws:
        - Assumptions
        - Limitations
        - Bias
        - Reproducibility issues
        - Overclaiming
        
        Paper Title: {title}
        Summary: {summary}
        Return bullet list of flaws."""
    )
    chain = prompt | llm
    state["flaws"] = chain.invoke({"title": state["paper"].title, "summary": state["summary"]}).content
    return state