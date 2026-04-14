"""
Neon PostgreSQL Database Module
Handles user management, paper history, and 10-day auto-destruct
"""
import os
from dotenv import load_dotenv
import psycopg2
from datetime import datetime, timedelta
from psycopg2.extras import RealDictCursor
import hashlib
import json
import logging

# Setup logging
logger = logging.getLogger(__name__)

# Load environment variables from .env file
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://user:password@localhost/paperintel")

def get_db_connection():
    """Get PostgreSQL connection"""
    conn = psycopg2.connect(DATABASE_URL)
    return conn

def init_neon_db():
    """Initialize database tables"""
    conn = get_db_connection()
    cur = conn.cursor()
    
    # Users table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            username VARCHAR(100) UNIQUE NOT NULL,
            password_hash VARCHAR(255) NOT NULL,
            created_at TIMESTAMP DEFAULT NOW(),
            updated_at TIMESTAMP DEFAULT NOW()
        );
    """)
    
    # Papers table with 10-day auto-destruct
    cur.execute("""
        CREATE TABLE IF NOT EXISTS papers (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            title VARCHAR(500) NOT NULL,
            knowledge_json TEXT,
            summary TEXT,
            flaws TEXT,
            comparison TEXT,
            ppt_file VARCHAR(500),
            s3_vector_key VARCHAR(500),
            created_at TIMESTAMP DEFAULT NOW(),
            expires_at TIMESTAMP DEFAULT NOW() + INTERVAL '10 days',
            FOREIGN KEY (user_id) REFERENCES users(id)
        );
    """)
    
    # Create index on expires_at for faster cleanup
    cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_papers_expires_at ON papers(expires_at);
    """)
    
    conn.commit()
    cur.close()
    conn.close()

def signup(username: str, password: str) -> bool:
    """Create new user account"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        cur.execute(
            "INSERT INTO users (username, password_hash) VALUES (%s, %s)",
            (username, password_hash)
        )
        conn.commit()
        cur.close()
        conn.close()
        return True
    except psycopg2.IntegrityError:
        # Username already exists
        conn.rollback()
        cur.close()
        conn.close()
        return False

def login(username: str, password: str) -> dict or None:
    """Verify user credentials"""
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    password_hash = hashlib.sha256(password.encode()).hexdigest()
    cur.execute(
        "SELECT id, username FROM users WHERE username = %s AND password_hash = %s",
        (username, password_hash)
    )
    
    user = cur.fetchone()
    cur.close()
    conn.close()
    
    if user:
        return dict(user)
    return None

def make_serializable(obj):
    """Recursively convert objects to JSON-serializable format"""
    if isinstance(obj, (str, int, float, bool, type(None))):
        return obj
    elif isinstance(obj, list):
        return [make_serializable(item) for item in obj]
    elif isinstance(obj, dict):
        return {k: make_serializable(v) for k, v in obj.items()}
    elif hasattr(obj, '__module__') and 'matplotlib' in obj.__module__:
        # Skip matplotlib figures
        return None
    elif isinstance(obj, (tuple, set)):
        return [make_serializable(item) for item in obj]
    elif hasattr(obj, '__dict__'):
        # Handle custom objects
        return {k: make_serializable(v) for k, v in obj.__dict__.items()}
    else:
        # Fallback - return string representation
        return str(obj)

def save_paper(user_id: int, paper, summary: str, flaws: str, comparison: str, ppt_file: str, s3_vector_key: str = None) -> int:
    """Save paper to 10-day history"""
    conn = get_db_connection()
    cur = conn.cursor()
    
    # Serialize paper object, filtering out non-serializable objects
    try:
        paper_data = {
            "__type__": "PaperKnowledge",
            "title": getattr(paper, "title", "Unknown"),
            "abstract": getattr(paper, "abstract", ""),
            "authors": getattr(paper, "authors", []),
            "venue": getattr(paper, "venue", ""),
            "year": getattr(paper, "year", ""),
            "pdf_path": getattr(paper, "pdf_path", "")
        }
        knowledge_json = json.dumps(paper_data)
    except Exception as e:
        # Fallback - just store title and basic info
        logger.warning(f"⚠️ Partial serialization: {str(e)}")
        knowledge_json = json.dumps({
            "__type__": "PaperKnowledge",
            "title": getattr(paper, "title", "Unknown")
        })
    
    expires_at = datetime.now() + timedelta(days=10)
    
    cur.execute("""
        INSERT INTO papers (user_id, title, knowledge_json, summary, flaws, comparison, ppt_file, s3_vector_key, expires_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING id;
    """, (user_id, paper.title, knowledge_json, summary, flaws, comparison, ppt_file, s3_vector_key, expires_at))
    
    paper_id = cur.fetchone()[0]
    conn.commit()
    cur.close()
    conn.close()
    
    return paper_id

def get_user_papers(user_id: int, limit: int = 10) -> list:
    """Get user's papers from last 10 days"""
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    # Clean up expired papers
    cur.execute("DELETE FROM papers WHERE expires_at < NOW();")
    conn.commit()
    
    cur.execute("""
        SELECT * FROM papers 
        WHERE user_id = %s AND expires_at > NOW()
        ORDER BY created_at DESC 
        LIMIT %s;
    """, (user_id, limit))
    
    papers = [dict(row) for row in cur.fetchall()]
    cur.close()
    conn.close()
    
    return papers

def get_paper_by_id(paper_id: int, user_id: int) -> dict or None:
    """Get specific paper by ID (belongs to user)"""
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    cur.execute("""
        SELECT * FROM papers 
        WHERE id = %s AND user_id = %s AND expires_at > NOW();
    """, (paper_id, user_id))
    
    result = cur.fetchone()
    paper = dict(result) if result else None
    cur.close()
    conn.close()
    
    return paper

def cleanup_expired_papers():
    """Cleanup expired papers (runs periodically)"""
    conn = get_db_connection()
    cur = conn.cursor()
    
    # Get S3 keys before deletion
    cur.execute("""
        SELECT s3_vector_key FROM papers WHERE expires_at < NOW() AND s3_vector_key IS NOT NULL;
    """)
    s3_keys = [row[0] for row in cur.fetchall()]
    
    # Delete expired papers
    cur.execute("DELETE FROM papers WHERE expires_at < NOW();")
    conn.commit()
    cur.close()
    conn.close()
    
    return s3_keys
