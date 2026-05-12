from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from config import LLM_MODEL, GROQ_API_KEY

llm = ChatGroq(model=LLM_MODEL, temperature=0.3, groq_api_key=GROQ_API_KEY)

def answer_general_question(state):
    context = "\n\n".join([c["text"] for c in state["chunks"][:20]])
    custom = state["router_decision"].get("custom_instructions", "")

    prompt = ChatPromptTemplate.from_template(
        """Answer the user's question about the paper with maximum accuracy and usefulness.

Paper Title: {title}
Retrieved Context:
{context}

User Question: {user_input}
Additional Instructions: {custom}

Answer directly, clearly, and comprehensively.
If the answer is not in the paper, say so honestly.
Cite relevant sections when possible."""
    )

    chain = prompt | llm
    state["qa_answer"] = chain.invoke({
        "title": state["paper"].title,
        "context": context,
        "user_input": state["user_instruction"],
        "custom": custom
    }).content
    return state