def personalize(state):
    parts = []
    if state.get("summary"):
        parts.append("📝 **Summary**\n" + state["summary"])
    if state.get("insights"):
        parts.append("💡 **Deep Insights**\n" + state["insights"])
    if state.get("flaws"):
        parts.append("🔍 **Flaws & Limitations**\n" + state["flaws"])
    if state.get("comparison"):
        parts.append("📊 **Comparison with Related Work**\n" + state["comparison"])
    if state.get("qa_answer"):
        parts.append("❓ **Answer to Your Question**\n" + state["qa_answer"])
    
    state["final_output"] = "\n\n".join(parts)
    return state