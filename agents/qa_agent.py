from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from config import LLM_MODEL

llm = ChatOpenAI(model=LLM_MODEL, temperature=0.3)

def answer_general_question(state):
    context = "\n\n".join([c["text"] for c in state["chunks"][:20]])
    custom = state["router_decision"].get("custom_instructions", "")
    
    prompt = ChatPromptTemplate.from_template(
        """Answer the user's question about the paper with maximum accuracy and usefulness.
        
Paper Title: {title}
Retrieved Context:
{context}

User question / instruction: {user_input}
Extra instructions: {custom}

Answer directly, clearly, and comprehensively."""
    )
    chain = prompt | llm
    state["qa_answer"] = chain.invoke({
        "title": state["paper"].title,
        "context": context,
        "user_input": state["user_instruction"],
        "custom": custom
    }).content
    return state