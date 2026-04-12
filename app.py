import streamlit as st
import json
from datetime import datetime
from ingestion.pdf_ingestor import IngestionAgent
from embedding.embedder import ChunkingEmbedder
from vectorstore.faiss_store import VectorMemory
from utils.arxiv_downloader import download_arxiv_paper
from graph.agent_graph import paper_graph
from output.ppt_generator import generate_ppt
from database import signup, login, save_paper, get_user_papers, init_db
from knowledge.schema import PaperKnowledge

st.set_page_config(page_title="🧠 Best Paper AI", layout="wide")
st.title("🧠 Best Research Paper AI Assistant")
st.caption("Tell me **anything** — Best Summary + Deep Insights + Flaws + PPT + Any Task")

init_db()

# Session state
if "user" not in st.session_state:
    st.session_state.user = None
if "current_paper" not in st.session_state:
    st.session_state.current_paper = None
if "messages" not in st.session_state:
    st.session_state.messages = []

# ====================== LOGIN / SIGNUP ======================
if st.session_state.user is None:
    tab1, tab2 = st.tabs(["🔑 Login", "✍️ Sign Up"])
    
    with tab1:
        username = st.text_input("Username", key="login_user")
        password = st.text_input("Password", type="password", key="login_pass")
        if st.button("Login"):
            user = login(username, password)
            if user:
                st.session_state.user = user
                st.success(f"Welcome back, {username}!")
                st.rerun()
            else:
                st.error("Invalid username or password")
    
    with tab2:
        new_user = st.text_input("Choose username", key="signup_user")
        new_pass = st.text_input("Choose password", type="password", key="signup_pass")
        if st.button("Create Account"):
            if signup(new_user, new_pass):
                st.success("Account created successfully! Please login.")
            else:
                st.error("Username already taken")

else:
    # ====================== LOGGED-IN INTERFACE ======================
    st.sidebar.success(f"👤 Logged in as: {st.session_state.user['username']}")
    if st.sidebar.button("Logout"):
        st.session_state.user = None
        st.rerun()

    # 10-Day Memory Sidebar
    st.sidebar.subheader("📜 Your 10-Day History")
    papers = get_user_papers(st.session_state.user["id"])
    for p in papers[:8]:
        if st.sidebar.button(f"📄 {p['title'][:40]}... ({p['date'][:10]})", key=f"hist_{p['id']}"):
            try:
                st.session_state.current_paper = PaperKnowledge(**json.loads(p.get("knowledge_json", "{}")))
                st.session_state.messages = [{"role": "assistant", "content": p.get("summary", "Paper loaded from memory")}]
                st.rerun()
            except:
                st.error("Could not load paper")

    # Main Area - Paper Input
    if not st.session_state.current_paper:
        st.subheader("Step 1: Load a Paper")
        col1, col2 = st.columns([1, 1])
        with col1:
            uploaded = st.file_uploader("Upload PDF", type="pdf")
            if uploaded:
                with open("temp.pdf", "wb") as f:
                    f.write(uploaded.getvalue())
                pdf_path = "temp.pdf"
        with col2:
            arxiv_input = st.text_input("Or enter arXiv ID/URL")
            if arxiv_input and st.button("Download from arXiv"):
                pdf_path = download_arxiv_paper(arxiv_input)

        if 'pdf_path' in locals() and st.button("🚀 Process Paper"):
            with st.spinner("Ingesting with GROBID + Creating embeddings..."):
                ingestor = IngestionAgent(use_grobid=True)
                embedder = ChunkingEmbedder()
                memory = VectorMemory()
                
                paper = ingestor.ingest(pdf_path)
                chunks = embedder.chunk_and_embed(paper)
                memory.add(chunks)
                
                st.session_state.current_paper = paper
                st.session_state.messages = []
                st.success(f"✅ Paper loaded: {paper.title}")
                st.rerun()

    else:
        # Chat Interface (like ChatGPT)
        st.subheader(f"Current Paper: **{st.session_state.current_paper.title}**")
        
        # Display conversation
        for msg in st.session_state.messages:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

        # User free-form input
        if user_input := st.chat_input("Ask anything or give instructions (e.g. 'Best summary with insights', 'Find flaws', 'Make PPT', 'Explain like 10')"):
            st.session_state.messages.append({"role": "user", "content": user_input})
            with st.chat_message("user"):
                st.markdown(user_input)

            with st.chat_message("assistant"):
                with st.spinner("Router analyzing your request → Running best agents..."):
                    result = paper_graph.invoke({
                        "paper": st.session_state.current_paper,
                        "user_instruction": user_input,
                        "chunks": [],
                        "summary": "",
                        "insights": "",
                        "flaws": "",
                        "comparison": "",
                        "qa_answer": "",
                        "mode": "researcher",
                        "final_output": "",
                        "ppt_file": ""
                    })

                    response = result.get("final_output") or result.get("summary", "Task completed.")

                    # Auto-generate PPT if requested
                    if "ppt" in result.get("router_decision", {}).get("tasks", []):
                        ppt_file = generate_ppt(
                            st.session_state.current_paper,
                            result.get("summary", ""),
                            result.get("flaws", ""),
                            result.get("comparison", ""),
                            st.session_state.user["id"]
                        )
                        result["ppt_file"] = ppt_file
                        response += f"\n\n📊 **PPT generated successfully!** Use history to download."

                    st.markdown(response)
                    st.session_state.messages.append({"role": "assistant", "content": response})

                    # Save conversation to 10-day memory
                    save_paper(
                        st.session_state.user["id"],
                        st.session_state.current_paper,
                        result.get("summary", ""),
                        result.get("flaws", ""),
                        result.get("comparison", ""),
                        result.get("ppt_file", "")
                    )

st.caption("💡 Pro tip: Be as specific as you want — the smarter your instruction, the better the output.")