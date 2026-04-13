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
from config import GROQ_API_KEY

st.set_page_config(
    page_title="🧠 PaperIntel AI",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for premium look
st.markdown("""
<style>
    .main {background-color: #0e1117;}
    .stChatMessage {border-radius: 12px;}
    .header {font-size: 2.2rem; font-weight: 700; color: #00d4ff;}
    .paper-title {font-size: 1.4rem; font-weight: 600; color: #ffffff;}
</style>
""", unsafe_allow_html=True)

init_db()

if "user" not in st.session_state:
    st.session_state.user = None
if "current_paper" not in st.session_state:
    st.session_state.current_paper = None
if "messages" not in st.session_state:
    st.session_state.messages = []

# ====================== SIDEBAR ======================
with st.sidebar:
    if st.session_state.user:
        st.success(f"👤 {st.session_state.user['username']}")
        if st.button("Logout", use_container_width=True):
            st.session_state.user = None
            st.rerun()

        st.subheader("📜 10-Day History")
        papers = get_user_papers(st.session_state.user["id"])
        if papers:
            for p in papers[:6]:
                if st.button(f"📄 {p['title'][:38]}...", key=f"hist_{p['id']}"):
                    try:
                        st.session_state.current_paper = PaperKnowledge(**json.loads(p.get("knowledge_json", "{}")))
                        st.session_state.messages = [{"role": "assistant", "content": "✅ Paper loaded from memory."}]
                        st.rerun()
                    except:
                        st.error("Could not load paper")
        else:
            st.info("No papers yet in last 10 days")
    else:
        st.info("Please login to save your work")

# ====================== MAIN UI ======================
st.markdown('<h1 class="header">🧠 PaperIntel AI</h1>', unsafe_allow_html=True)
st.caption("Advanced Research Paper Assistant • Powered by Groq • Professional Summaries • Insights • PPT • Real-World Applications")

if st.session_state.user is None:
    tab1, tab2 = st.tabs(["🔑 Login", "✍️ Sign Up"])
    
    with tab1:
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        if st.button("Login", type="primary"):
            user = login(username, password)
            if user:
                st.session_state.user = user
                st.success("Login successful!")
                st.rerun()
            else:
                st.error("Invalid credentials")

    with tab2:
        new_user = st.text_input("Choose username")
        new_pass = st.text_input("Choose password", type="password")
        if st.button("Create Account", type="primary"):
            if signup(new_user, new_pass):
                st.success("Account created! Please login.")
            else:
                st.error("Username already taken")

else:
    # Paper Input Section
    if not st.session_state.current_paper:
        st.subheader("Upload or Load a Research Paper")
        col1, col2 = st.columns([1, 1])
        
        with col1:
            uploaded = st.file_uploader("Upload PDF", type="pdf")
            if uploaded:
                with open("temp.pdf", "wb") as f:
                    f.write(uploaded.getvalue())
                pdf_path = "temp.pdf"
        
        with col2:
            arxiv_input = st.text_input("Or enter arXiv ID / URL")
            if arxiv_input and st.button("Download from arXiv", type="primary"):
                pdf_path = download_arxiv_paper(arxiv_input)

        if 'pdf_path' in locals() and st.button("🚀 Process Paper", type="primary", use_container_width=True):
            with st.spinner("Ingesting paper with GROBID + Groq AI..."):
                ingestor = IngestionAgent(use_grobid=True)
                embedder = ChunkingEmbedder()
                memory = VectorMemory()
                
                paper = ingestor.ingest(pdf_path)
                chunks = embedder.chunk_and_embed(paper)
                memory.add(chunks)
                
                st.session_state.current_paper = paper
                st.session_state.messages = []
                st.success(f"✅ Paper loaded: **{paper.title}**")
                st.rerun()

    else:
        # Paper Loaded - Chat Interface
        st.markdown(f"**Current Paper:** {st.session_state.current_paper.title}")
        
        # Chat History
        for msg in st.session_state.messages:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

        # User Input
        if user_input := st.chat_input("Ask anything about this paper... (e.g., best summary, make PPT, clinical applications, flaws...)"):
            st.session_state.messages.append({"role": "user", "content": user_input})
            with st.chat_message("user"):
                st.markdown(user_input)

            with st.chat_message("assistant"):
                with st.spinner("🤖 Router analyzing → Running specialized agents..."):
                    result = paper_graph.invoke({
                        "paper": st.session_state.current_paper,
                        "user_instruction": user_input,
                        "chunks": [],
                        "summary": "", "insights": "", "flaws": "", 
                        "comparison": "", "qa_answer": "", 
                        "ppt_outline": "", "application": "",
                        "mode": "researcher", "final_output": "", "ppt_file": ""
                    })

                    final_response = result.get("final_output") or result.get("summary", "✅ Task completed.")

                    # Display structured outputs nicely
                    if result.get("application"):
                        with st.expander("💼 Real-World Applications", expanded=True):
                            st.markdown(result["application"])
                    
                    if result.get("ppt_outline"):
                        with st.expander("📊 PPT Outline Generated", expanded=True):
                            st.markdown(result["ppt_outline"])
                        if result.get("ppt_file"):
                            with open(result["ppt_file"], "rb") as f:
                                st.download_button("⬇️ Download PowerPoint", f, file_name="Paper_Presentation.pptx", use_container_width=True)

                    st.markdown(final_response)
                    st.session_state.messages.append({"role": "assistant", "content": final_response})

                    # Save to 10-day memory
                    save_paper(
                        st.session_state.user["id"],
                        st.session_state.current_paper,
                        result.get("summary", ""),
                        result.get("flaws", ""),
                        result.get("comparison", ""),
                        result.get("ppt_file", "")
                    )

st.caption("🧠 Professional Research Paper Intelligence • Powered by Harshit Rai • Built for accuracy & real-world use")