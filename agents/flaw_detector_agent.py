from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from config import LLM_MODEL, GROQ_API_KEY

llm = ChatGroq(model=LLM_MODEL, temperature=0.2, groq_api_key=GROQ_API_KEY)

def detect_flaws(state):
    prompt = ChatPromptTemplate.from_template(
        """You are a harsh, world-class academic reviewer.
Analyze the methodology and results of this paper with extreme rigor.

Paper Title: {title}
Summary: {summary}

Identify ALL possible flaws and weaknesses. Be strict and specific.
Categories to cover:
- Fundamental assumptions
- Methodological limitations
- Potential biases
- Reproducibility issues
- Overclaiming or exaggeration
- Statistical or experimental weaknesses
- Generalization problems

Return only a clear, well-organized bullet list of flaws. Do not be polite."""
    )
    chain = prompt | llm
    state["flaws"] = chain.invoke({
        "title": state["paper"].title,
        "summary": state["summary"]
    }).content
    return state