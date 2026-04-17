# 📚 PaperIntel AI - Research Paper Summarizer & Analysis System

A production-ready AI-powered research paper analysis platform using LangGraph, FastAPI, and Groq LLM. Automatically summarizes, analyzes, and generates insights from academic papers with advanced agent-based workflows.

---

## 🎯 Project Overview

**PaperIntel AI** is an intelligent research paper processing system that:

- 📄 **Extracts & Parses PDFs** using GROBID and PyMuPDF with structural understanding
- 🧠 **Generates Smart Summaries** with key contributions, methodology, results, and limitations
- 🔍 **Detects Flaws & Gaps** in research methodology and findings
- 💡 **Generates Insights** with real-world applications and connections to related work
- 📊 **Creates Presentations** (PPT format) automatically from paper analysis
- 🎓 **Answers Q&A** on paper content using semantic retrieval
- 🚀 **Personalized Analysis** tailored to user expertise level

### Key Technologies

- **LLM Backend**: Groq (llama-3.3-70b-versatile) - Free, fast, powerful
- **Agent Framework**: LangGraph for multi-agent orchestration
- **Vector Storage**: FAISS for semantic search
- **Web Framework**: FastAPI for REST API
- **Database**: PostgreSQL (Neon) for user management
- **Caching**: Redis for response caching
- **PDF Parsing**: GROBID + PyMuPDF for structural extraction
- **Embeddings**: Scibert (allenai/scibert_scivocab_uncased) - optimized for research papers

---

## 🏗️ Architecture

### Multi-Agent Pipeline

```
User Input
    ↓
Router Agent (Decision Making)
    ↓
Retriever Agent (Semantic Search)
    ↓
Summarizer Agent → Insight Agent → Flaw Detector Agent
    ↓
Context Agent (Related Work) → QA Agent (if needed)
    ↓
Personalization Agent (Tailor Output)
    ↓
PPT Agent → Application Agent
    ↓
Final Output (Summary, Insights, Flaws, Comparison, Q&A, PPT)
```

### Directory Structure

```
research-paper-summarizer/
├── main.py                    # CLI entry point
├── main_fastapi.py           # FastAPI web application
├── config.py                 # Configuration management
├── agents/                   # AI agents
│   ├── router_agent.py       # Route user requests
│   ├── retriever_agent.py    # Semantic retrieval
│   ├── summarizer_agent.py   # Generate summaries
│   ├── insight_agent.py      # Extract insights
│   ├── flaw_detector_agent.py# Identify flaws
│   ├── context_agent.py      # Find related work
│   ├── qa_agent.py           # Answer questions
│   ├── personalization_agent.py # Tailor to user
│   ├── ppt_agent.py          # Generate presentations
│   └── application_agent.py   # Real-world applications
├── ingestion/                # PDF ingestion
│   ├── pdf_ingestor.py       # PDF parsing
│   └── grobid_parser.py      # GROBID integration
├── embedding/                # Embedding & chunking
│   └── embedder.py           # Scibert embeddings
├── vectorstore/              # Vector storage
│   └── faiss_store.py        # FAISS vector store
├── knowledge/                # Data models
│   └── schema.py             # PaperKnowledge schema
├── output/                   # Output generation
│   └── ppt_generator.py      # PowerPoint creation
├── graph/                    # Workflow orchestration
│   └── agent_graph.py        # LangGraph workflow
├── database.py               # SQLite (local)
├── database_neon.py          # PostgreSQL (production)
├── cache_manager.py          # Response caching
├── s3_faiss_manager.py       # S3 storage for vectors
├── requirements.txt          # Python dependencies
├── Dockerfile                # Container build
├── docker-compose.yaml       # Local development setup
└── templates/                # HTML templates (FastAPI)
```

---

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- GROBID service running (optional but recommended)
- Redis (for caching)
- PostgreSQL Neon account (for production)

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/Harshitraiii2005/research-paper-summarizer.git
   cd research-paper-summarizer
   ```

2. **Set up environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your API keys
   # Required: GROQ_API_KEY, DATABASE_URL (for production)
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Start GROBID service (optional)**
   ```bash
   docker run --rm -p 8070:8070 -t grobid/grobid:0.8.0
   ```

5. **Start Redis (optional)**
   ```bash
   redis-server --port 6380
   ```

### Usage

#### CLI Mode (Local)
```bash
python main.py
# Enter PDF path or arXiv ID (e.g., arxiv.org/abs/2312.13345)
# Specify your request (e.g., "Give best summary with insights")
# Get comprehensive paper analysis
```

#### Web API (FastAPI)
```bash
uvicorn main_fastapi:app --reload --port 8001
# Visit http://localhost:8001
# Upload PDF, get analysis in browser
```

---

## 📋 Features

### 1. **Smart Summarization**
- Extracts key contributions
- Explains methodology
- Highlights main results
- Identifies limitations
- Structured format for easy reading

### 2. **Flaw Detection**
- Methodology gaps
- Statistical issues
- Unsubstantiated claims
- Reproducibility concerns
- Generalization problems

### 3. **Insight Generation**
- Real-world applications
- Impact assessment
- Future research directions
- Connection to existing literature
- Practical implications

### 4. **Context Analysis**
- Related work comparison
- State-of-the-art positioning
- Citation network insights
- Research trend alignment

### 5. **Automatic Presentations**
- Title slide with authors
- Summary slide
- Flaws & limitations
- Comparison with related work
- Professional PPTX format

### 6. **Q&A System**
- Answer arbitrary questions about the paper
- Semantic search on paper content
- Context-aware responses
- Citation-based answers

---

## 🔧 Configuration

### Environment Variables (.env)
```bash
# API Keys
GROQ_API_KEY=your_groq_api_key_here
OPENAI_API_KEY=your_openai_key_here (optional, for future use)

# Database
DATABASE_URL=postgresql://user:password@localhost/paperintel

# Services
GROBID_URL=http://localhost:8070
REDIS_URL=redis://localhost:6380

# AWS S3 (optional)
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key
AWS_S3_BUCKET=your_bucket_name
```

### config.py
```python
LLM_MODEL = "llama-3.3-70b-versatile"  # Groq model
EMBEDDING_MODEL = "allenai/scibert_scivocab_uncased"  # SciBERT
GROBID_URL = "http://localhost:8070"
```

---

## 📦 Dependencies

### Core
- **langchain 0.1.0** - LLM framework
- **langgraph 0.0.24** - Multi-agent orchestration
- **langchain-groq 0.0.1** - Groq integration
- **groq 0.4.1** - Groq API client

### Web
- **fastapi 0.104.1** - REST API framework
- **uvicorn[standard] 0.24.0** - ASGI server
- **starlette 0.27.0** - Web framework

### Data Processing
- **pymupdf, pymupdf4llm** - PDF extraction
- **pypdf 3.17.1** - PDF manipulation
- **sentence-transformers 2.2.0** - Embeddings
- **faiss-cpu 1.7.4** - Vector search

### Storage
- **psycopg2-binary 2.9.9** - PostgreSQL driver
- **redis 5.0.1** - Caching layer
- **boto3 1.29.7** - AWS S3 integration

### Utilities
- **pydantic 2.5.0** - Data validation
- **python-dotenv 1.0.0** - Environment management
- **python-pptx 0.6.21** - PowerPoint generation
- **arxiv 1.4.8** - arXiv paper download

---

## 🐳 Docker Deployment

### Build Image
```bash
docker build -t paperintel:latest .
```

### Run Container
```bash
docker run -p 8000:8000 \
  -e GROQ_API_KEY=your_key \
  -e DATABASE_URL=postgresql://... \
  -v ./user_data:/app/user_data \
  paperintel:latest
```

### Docker Compose (Development)
```bash
docker-compose up -d
# Services: FastAPI (8000), GROBID (8070), PostgreSQL, Redis
```

---

## 🧪 Testing

### Run Tests
```bash
pytest tests/ -v
pytest tests/test_agents.py -v  # Agent-specific tests
```

### Manual Testing
```bash
# Test PDF ingestion
python -c "from ingestion.pdf_ingestor import IngestionAgent; print('✅ Ingestion OK')"

# Test embeddings
python -c "from embedding.embedder import ChunkingEmbedder; print('✅ Embeddings OK')"

# Test LLM connection
python -c "from langchain_groq import ChatGroq; print('✅ Groq Connected')"
```

---

## 🔐 Security & Best Practices

### For Production:
- ✅ Use environment variables for secrets (never commit .env)
- ✅ Enable database connection pooling
- ✅ Set up Redis authentication
- ✅ Use HTTPS for API endpoints
- ✅ Implement rate limiting (FastAPI middleware)
- ✅ Add authentication & authorization (JWT tokens)
- ✅ Use health check endpoints
- ✅ Set up proper logging & monitoring

### Recommended Additions:
```python
# Add to main_fastapi.py for production
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter
from slowapi.util import get_remote_address

app.add_middleware(CORSMiddleware, allow_origins=["*"])
limiter = Limiter(key_func=get_remote_address)
```

---

## 📊 Performance Considerations

### Optimization Strategies:
1. **Caching**: Redis caches similar papers' analysis
2. **Batch Processing**: Process multiple papers in parallel
3. **Vector Storage**: S3 + FAISS for scalable embeddings
4. **Database**: Connection pooling via psycopg2
5. **PDF Parsing**: GROBID for structured extraction
6. **Async APIs**: FastAPI's native async support

### Benchmarks:
- Single paper analysis: ~15-30 seconds (with GROBID)
- Summary generation: ~3-5 seconds
- PPT creation: ~2 seconds
- Embeddings for 100 chunks: ~1 second

---

## 🚦 API Endpoints (FastAPI)

```
POST   /upload/              - Upload PDF for analysis
GET    /papers/              - List user's papers
GET    /papers/{id}          - Get paper details & analysis
GET    /papers/{id}/ppt      - Download generated PPT
POST   /papers/{id}/ask      - Ask question about paper
POST   /analyze              - Submit arXiv URL for analysis
GET    /health               - Health check
```

---

## 🤝 Contributing

1. Fork the repository
2. Create feature branch: `git checkout -b feature/your-feature`
3. Commit changes: `git commit -m "Add your feature"`
4. Push to branch: `git push origin feature/your-feature`
5. Open Pull Request

---

## 📝 License

This project is licensed under the MIT License - see LICENSE file for details.

---

## 💡 Future Enhancements

- [ ] Multi-language support for papers
- [ ] Collaborative annotations & discussions
- [ ] Citation graph analysis
- [ ] Trend detection across paper corpus
- [ ] Integration with academic databases (CrossRef, OpenAlex)
- [ ] Advanced visualization dashboards
- [ ] Export to multiple formats (Markdown, JSON, etc.)
- [ ] Fine-tuned models for specific research domains

---

## 📞 Support

For issues, questions, or suggestions:
- Open an issue on GitHub
- Contact: [Your Email]
- Documentation: [Wiki/Docs Link]

---

## 🙏 Acknowledgments

- Groq for the powerful free LLM API
- GROBID for scientific document parsing
- LangChain & LangGraph for agent orchestration
- FastAPI for the web framework
- Neon for PostgreSQL hosting

---

**Built with ❤️ for research paper analysis**

*Last Updated: April 2026*
