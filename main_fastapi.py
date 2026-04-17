"""
Main FastAPI Application
Production-ready FastAPI backend for PaperIntel AI
"""
import os
from dotenv import load_dotenv
import json
import logging
from fastapi import FastAPI, Request, Depends, HTTPException, File, UploadFile, Form
from fastapi.responses import HTMLResponse, FileResponse, StreamingResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
from contextlib import asynccontextmanager
import tempfile
from pathlib import Path

# Load environment variables from .env file
load_dotenv()

# Import modules
from database_neon import init_neon_db, signup, login, save_paper, get_user_papers, get_paper_by_id
from cache_manager import get_cached_response, cache_response
from s3_faiss_manager import (
    upload_vectors_to_s3, download_vectors_from_s3, check_vectors_exist,
    generate_vector_key, ensure_s3_bucket_exists, cleanup_expired_vectors
)
from loading_messages import get_loading_messages_sequence, get_random_loading_message
from ingestion.pdf_ingestor import IngestionAgent
from embedding.embedder import ChunkingEmbedder
from vectorstore.faiss_store import VectorMemory
from utils.arxiv_downloader import download_arxiv_paper
from graph.agent_graph import paper_graph
from knowledge.schema import PaperKnowledge

# Logging setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ====================== STARTUP/SHUTDOWN ======================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events"""
    logger.info("🚀 Starting PaperIntel AI FastAPI server...")
    
    # Initialize databases
    init_neon_db()
    #ensure_s3_bucket_exists()
    
    logger.info("✅ All systems initialized")
    yield
    
    logger.info("🛑 Shutting down PaperIntel AI")

# ====================== APP SETUP ======================

app = FastAPI(
    title="PaperIntel AI",
    description="Advanced Research Paper Assistant",
    version="1.0.0",
    lifespan=lifespan
)

# Session middleware
app.add_middleware(SessionMiddleware, secret_key=os.getenv("SECRET_KEY", "your-secret-key-change-in-production"))

# Mount static files
STATIC_DIR = Path(__file__).parent / "static"
STATIC_DIR.mkdir(exist_ok=True)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# Jinja2 templates
TEMPLATES_DIR = Path(__file__).parent / "templates"
TEMPLATES_DIR.mkdir(exist_ok=True)
templates = Jinja2Templates(directory=TEMPLATES_DIR)

# ====================== UTILITY FUNCTIONS ======================

def get_current_user(request: Request) -> dict:
    """Get current user from session"""
    user = request.session.get("user")
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user

def deserialize_paper(knowledge_json: str) -> PaperKnowledge:
    """Deserialize PaperKnowledge from JSON"""
    data = json.loads(knowledge_json)
    if isinstance(data, dict) and data.get("__type__") == "PaperKnowledge":
        clean_data = {k: v for k, v in data.items() if k != "__type__"}
        return PaperKnowledge(**clean_data)
    return PaperKnowledge(**data)

def serialize_result(obj):
    """Recursively serialize result to JSON-safe format"""
    if isinstance(obj, (str, int, float, bool, type(None))):
        return obj
    elif isinstance(obj, list):
        return [serialize_result(item) for item in obj]
    elif isinstance(obj, dict):
        return {k: serialize_result(v) for k, v in obj.items()}
    elif isinstance(obj, PaperKnowledge):
        # Skip PaperKnowledge objects
        return None
    elif hasattr(obj, '__module__') and 'matplotlib' in obj.__module__:
        # Skip matplotlib figures
        return None
    else:
        # Return string representation for other objects
        return str(obj)

async def stream_loading_messages():
    """Stream funny loading messages as SSE"""
    messages = get_loading_messages_sequence()
    for message in messages:
        yield f"data: {json.dumps({'message': message})}\n\n"

async def stream_chat_with_messages(paper, query, chunks, paper_data, user_id):
    """Stream chat response with loading messages"""
    import asyncio
    import time
    
    messages = get_loading_messages_sequence()
    msg_index = 0
    
    # Stream loading messages
    while msg_index < len(messages):
        message = messages[msg_index]
        logger.info(f"Streaming message {msg_index + 1}/{len(messages)}: {message[:50]}...")
        yield f"data: {json.dumps({'type': 'message', 'content': message})}\n\n"
        msg_index += 1
        await asyncio.sleep(0.3)  # Reduced delay for faster streaming
    
    # Process query in background
    try:
        # Run agentic pipeline
        result = paper_graph.invoke({
            "paper": paper,
            "user_instruction": query,
            "chunks": chunks,
            "summary": "", "insights": "", "flaws": "", 
            "comparison": "", "qa_answer": "", 
            "ppt_outline": "", "application": "",
            "mode": "researcher", "final_output": "", "ppt_file": ""
        })
        
        # Serialize result
        result = serialize_result(result)
        
        # Cache the result
        cache_response(paper.title, query, result)
        
        # Save paper with updated data
        save_paper(
            user_id,
            paper,
            summary=result.get("summary", "") if result else "",
            flaws=result.get("flaws", "") if result else "",
            comparison=result.get("comparison", "") if result else "",
            ppt_file=result.get("ppt_file", "") if result else "",
            s3_vector_key=paper_data.get("s3_vector_key")
        )
        
        result["from_cache"] = False
        
        # Send final result
        yield f"data: {json.dumps({'type': 'result', 'content': result})}\n\n"
        
    except Exception as e:
        logger.error(f"Chat stream error: {str(e)}")
        yield f"data: {json.dumps({'type': 'error', 'content': str(e)})}\n\n"

# ====================== ROUTES: AUTHENTICATION ======================

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Home page - redirects to dashboard or login"""
    user = request.session.get("user")
    if user:
        return RedirectResponse(url="/dashboard", status_code=302)
    
    return templates.TemplateResponse("login.html", {"request": request})

@app.get("/login", response_class=HTMLResponse)
async def get_login(request: Request):
    """Get login page"""
    user = request.session.get("user")
    if user:
        return RedirectResponse(url="/dashboard", status_code=302)
    
    return templates.TemplateResponse("login.html", {"request": request})

@app.post("/api/login")
async def post_login(request: Request):
    """Login endpoint"""
    try:
        data = await request.json()
        username = data.get("username")
        password = data.get("password")
        
        if not username or not password:
            return JSONResponse({"error": "Missing credentials"}, status_code=400)
        
        user = login(username, password)
        if not user:
            return JSONResponse({"error": "Invalid credentials"}, status_code=401)
        
        request.session["user"] = user
        return JSONResponse({"success": True, "redirect": "/dashboard"})
        
    except Exception as e:
        logger.error(f"Login error: {str(e)}")
        return JSONResponse({"error": "Server error"}, status_code=500)

@app.post("/api/signup")
async def post_signup(request: Request):
    """Signup endpoint"""
    try:
        data = await request.json()
        username = data.get("username")
        password = data.get("password")
        confirm_password = data.get("confirm_password")
        
        if not username or not password or not confirm_password:
            return JSONResponse({"error": "Missing fields"}, status_code=400)
        
        if password != confirm_password:
            return JSONResponse({"error": "Passwords don't match"}, status_code=400)
        
        if len(password) < 6:
            return JSONResponse({"error": "Password must be at least 6 characters"}, status_code=400)
        
        if signup(username, password):
            return JSONResponse({"success": True, "message": "Account created! Please login."})
        else:
            return JSONResponse({"error": "Username already taken"}, status_code=409)
            
    except Exception as e:
        logger.error(f"Signup error: {str(e)}")
        return JSONResponse({"error": "Server error"}, status_code=500)

@app.post("/api/logout")
async def logout(request: Request):
    """Logout endpoint"""
    request.session.clear()
    return JSONResponse({"success": True})

# ====================== ROUTES: DASHBOARD ======================

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    """Main dashboard"""
    user = request.session.get("user")
    if not user:
        return RedirectResponse(url="/login", status_code=302)
    
    papers = get_user_papers(user["id"])
    return templates.TemplateResponse(
        "dashboard.html",
        {"request": request, "user": user, "papers": papers}
    )

# ====================== ROUTES: PAPER MANAGEMENT ======================

@app.post("/api/upload-paper")
async def upload_paper(request: Request, file: UploadFile = File(...), user: dict = Depends(get_current_user)):
    """Upload and process PDF paper"""
    try:
        # Save uploaded file temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
            content = await file.read()
            tmp_file.write(content)
            pdf_path = tmp_file.name
        
        # Check if vectors already exist (skip if S3 not available)
        try:
            if check_vectors_exist(file.filename, user["id"]):
                return JSONResponse({
                    "status": "cached",
                    "message": "Paper already processed. Loading from cache..."
                })
        except Exception as e:
            logger.warning(f"⚠️ S3 check skipped: {str(e)}")
        
        # Ingest paper
        ingestor = IngestionAgent(use_grobid=True)
        paper = ingestor.ingest(pdf_path)
        
        # Embed and store vectors
        embedder = ChunkingEmbedder()
        chunks = embedder.chunk_and_embed(paper)
        
        # Upload vectors to S3 (skip if not available)
        s3_key = None
        try:
            s3_key = upload_vectors_to_s3(chunks, paper.title, user["id"])
        except Exception as e:
            logger.warning(f"⚠️ S3 upload skipped: {str(e)}")
        
        # Save to database
        paper_id = save_paper(
            user["id"],
            paper,
            summary="",
            flaws="",
            comparison="",
            ppt_file="",
            s3_vector_key=s3_key
        )
        
        # Clean up temp file
        os.unlink(pdf_path)
        
        return JSONResponse({
            "status": "success",
            "paper_id": paper_id,
            "title": paper.title,
            "s3_key": s3_key
        })
        
    except Exception as e:
        logger.error(f"Upload error: {str(e)}")
        error_str = str(e).lower()
        
        # Handle rate limit gracefully
        if "429" in str(e) or "rate limit" in error_str or "tokens per day" in error_str:
            return JSONResponse({
                "error": "API rate limit reached. Please try again later.",
                "code": "rate_limit"
            }, status_code=429)
        
        # Handle other errors
        return JSONResponse({"error": str(e)}, status_code=500)

@app.post("/api/arxiv-download")
async def arxiv_download(request: Request, user: dict = Depends(get_current_user)):
    """Download paper from arXiv"""
    try:
        data = await request.json()
        arxiv_url = data.get("url")
        
        if not arxiv_url:
            return JSONResponse({"error": "Missing arXiv URL"}, status_code=400)
        
        pdf_path = download_arxiv_paper(arxiv_url)
        
        if not pdf_path:
            return JSONResponse({"error": "Failed to download paper"}, status_code=400)
        
        # Ingest paper
        ingestor = IngestionAgent(use_grobid=True)
        paper = ingestor.ingest(pdf_path)
        
        # Embed and store vectors
        embedder = ChunkingEmbedder()
        chunks = embedder.chunk_and_embed(paper)
        
        # Upload vectors to S3 (skip if not available)
        s3_key = None
        try:
            s3_key = upload_vectors_to_s3(chunks, paper.title, user["id"])
        except Exception as e:
            logger.warning(f"⚠️ S3 upload skipped: {str(e)}")
        
        # Save to database
        paper_id = save_paper(
            user["id"],
            paper,
            summary="",
            flaws="",
            comparison="",
            ppt_file="",
            s3_vector_key=s3_key
        )
        
        # Clean up temp file
        os.unlink(pdf_path)
        
        return JSONResponse({
            "status": "success",
            "paper_id": paper_id,
            "title": paper.title
        })
        
    except Exception as e:
        logger.error(f"ArXiv download error: {str(e)}")
        return JSONResponse({"error": str(e)}, status_code=500)

@app.get("/api/paper/{paper_id}", response_class=HTMLResponse)
async def get_paper(paper_id: int, request: Request, user: dict = Depends(get_current_user)):
    """Get paper and chat interface"""
    paper_data = get_paper_by_id(paper_id, user["id"])
    
    if not paper_data:
        return JSONResponse({"error": "Paper not found"}, status_code=404)
    
    # Deserialize paper
    paper = deserialize_paper(paper_data["knowledge_json"])
    
    # Load vectors from S3 if available
    chunks = []
    if paper_data["s3_vector_key"]:
        chunks = download_vectors_from_s3(paper_data["s3_vector_key"]) or []
    
    return templates.TemplateResponse(
        "chat.html",
        {
            "request": request,
            "user": user,
            "paper_id": paper_id,
            "paper_title": paper.title,
            "paper": paper
        }
    )

@app.get("/api/papers")
async def get_papers_list(user: dict = Depends(get_current_user)):
    """Get user's paper history"""
    papers = get_user_papers(user["id"])
    # Convert any remaining datetime objects to ISO format
    for paper in papers:
        for key in ['created_at', 'expires_at', 'updated_at']:
            if key in paper and hasattr(paper[key], 'isoformat'):
                paper[key] = paper[key].isoformat()
    return JSONResponse(papers)

# ====================== ROUTES: CHAT & ANALYSIS ======================

@app.get("/api/chat/stream-loading")
async def stream_loading(request: Request, user: dict = Depends(get_current_user)):
    """Stream loading messages as Server-Sent Events"""
    return StreamingResponse(stream_loading_messages(), media_type="text/event-stream")

@app.post("/api/chat-stream")
async def chat_stream(request: Request, user: dict = Depends(get_current_user)):
    """Process user query with streaming loading messages"""
    async def generate():
        try:
            data = await request.json()
            paper_id = data.get("paper_id")
            query = data.get("query")
            
            if not paper_id or not query:
                yield f"data: {json.dumps({'type': 'error', 'content': 'Missing parameters'})}\n\n"
                return
            
            # Get paper from database
            paper_data = get_paper_by_id(paper_id, user["id"])
            if not paper_data:
                yield f"data: {json.dumps({'type': 'error', 'content': 'Paper not found'})}\n\n"
                return
            
            paper = deserialize_paper(paper_data["knowledge_json"])
            
            # Check cache first
            cached_result = get_cached_response(paper.title, query)
            if cached_result:
                cached_result["from_cache"] = True
                yield f"data: {json.dumps({'type': 'cached', 'content': '✅ Loaded from cache!'})}\n\n"
                yield f"data: {json.dumps({'type': 'result', 'content': cached_result})}\n\n"
                return
            
            # Load vectors from S3
            chunks = []
            if paper_data.get("s3_vector_key"):
                chunks = download_vectors_from_s3(paper_data["s3_vector_key"]) or []
            
            # Stream with loading messages
            async for chunk in stream_chat_with_messages(paper, query, chunks, paper_data, user["id"]):
                yield chunk
                
        except Exception as e:
            logger.error(f"Chat stream error: {str(e)}")
            yield f"data: {json.dumps({'type': 'error', 'content': str(e)})}\n\n"
    
    return StreamingResponse(generate(), media_type="text/event-stream")

@app.post("/api/chat")
async def chat(request: Request, user: dict = Depends(get_current_user)):
    """Process user query with agentic pipeline"""
    try:
        data = await request.json()
        paper_id = data.get("paper_id")
        query = data.get("query")
        
        if not paper_id or not query:
            return JSONResponse({"error": "Missing parameters"}, status_code=400)
        
        # Get paper from database
        paper_data = get_paper_by_id(paper_id, user["id"])
        if not paper_data:
            return JSONResponse({"error": "Paper not found"}, status_code=404)
        
        paper = deserialize_paper(paper_data["knowledge_json"])
        
        # Check cache first
        cached_result = get_cached_response(paper.title, query)
        if cached_result:
            cached_result["from_cache"] = True
            return JSONResponse(cached_result)
        
        # Load vectors from S3
        chunks = []
        if paper_data.get("s3_vector_key"):
            chunks = download_vectors_from_s3(paper_data["s3_vector_key"]) or []
        
        # Run agentic pipeline
        result = paper_graph.invoke({
            "paper": paper,
            "user_instruction": query,
            "chunks": chunks,
            "summary": "", "insights": "", "flaws": "", 
            "comparison": "", "qa_answer": "", 
            "ppt_outline": "", "application": "",
            "mode": "researcher", "final_output": "", "ppt_file": ""
        })
        
        # Serialize result to JSON-safe format
        result = serialize_result(result)
        
        # Cache the result
        cache_response(paper.title, query, result)
        
        # Save paper with updated data
        save_paper(
            user["id"],
            paper,
            summary=result.get("summary", "") if result else "",
            flaws=result.get("flaws", "") if result else "",
            comparison=result.get("comparison", "") if result else "",
            ppt_file=result.get("ppt_file", "") if result else "",
            s3_vector_key=paper_data["s3_vector_key"]
        )
        
        result["from_cache"] = False
        return JSONResponse(result)
        
    except Exception as e:
        logger.error(f"Chat error: {str(e)}")
        return JSONResponse({"error": str(e)}, status_code=500)

@app.get("/api/download-ppt/{paper_id}")
async def download_ppt(paper_id: int, user: dict = Depends(get_current_user)):
    """Download generated PPT"""
    try:
        paper_data = get_paper_by_id(paper_id, user["id"])
        if not paper_data or not paper_data["ppt_file"]:
            return JSONResponse({"error": "PPT not found"}, status_code=404)
        
        ppt_path = paper_data["ppt_file"]
        if not os.path.exists(ppt_path):
            return JSONResponse({"error": "PPT file not found"}, status_code=404)
        
        return FileResponse(
            ppt_path,
            filename="Paper_Presentation.pptx",
            media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation"
        )
        
    except Exception as e:
        logger.error(f"Download error: {str(e)}")
        return JSONResponse({"error": str(e)}, status_code=500)

@app.delete("/api/paper/{paper_id}")
async def delete_paper(paper_id: int, user: dict = Depends(get_current_user)):
    """Delete paper from history"""
    # TODO: Implement deletion with S3 cleanup
    return JSONResponse({"success": True})

# ====================== ERROR HANDLERS ======================

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle HTTP exceptions"""
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.detail}
    )

# ====================== HEALTH CHECK ======================

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return JSONResponse({
        "status": "ok",
        "service": "PaperIntel AI",
        "version": "1.0.0"
    })

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main_fastapi:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
