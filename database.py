import sqlite3
import hashlib
import json
from datetime import datetime, timedelta
from pathlib import Path
from knowledge.schema import PaperKnowledge

DB_PATH = "paper_agent.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    c.execute('''CREATE TABLE IF NOT EXISTS users (
                 id INTEGER PRIMARY KEY AUTOINCREMENT,
                 username TEXT UNIQUE NOT NULL,
                 password_hash TEXT NOT NULL,
                 created_at TEXT NOT NULL)''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS user_papers (
                 id INTEGER PRIMARY KEY AUTOINCREMENT,
                 user_id INTEGER NOT NULL,
                 title TEXT NOT NULL,
                 knowledge_json TEXT NOT NULL,
                 summary TEXT,
                 flaws TEXT,
                 comparison TEXT,
                 ppt_filename TEXT,
                 timestamp TEXT NOT NULL,
                 expires_at TEXT NOT NULL,
                 FOREIGN KEY(user_id) REFERENCES users(id))''')
    
    conn.commit()
    conn.close()
    cleanup_old_data()

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

def signup(username: str, password: str) -> bool:
    init_db()
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    try:
        c.execute("INSERT INTO users (username, password_hash, created_at) VALUES (?, ?, ?)",
                  (username, hash_password(password), datetime.now().isoformat()))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

def login(username: str, password: str) -> dict | None:
    init_db()
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT id, username FROM users WHERE username = ? AND password_hash = ?",
              (username, hash_password(password)))
    user = c.fetchone()
    conn.close()
    return {"id": user[0], "username": user[1]} if user else None

def save_paper(user_id: int, paper: PaperKnowledge, summary: str, flaws: str, comparison: str, ppt_filename: str):
    init_db()
    knowledge_json = json.dumps(paper.model_dump())
    now = datetime.now()
    expires = now + timedelta(days=10)
    
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''INSERT INTO user_papers 
                 (user_id, title, knowledge_json, summary, flaws, comparison, ppt_filename, timestamp, expires_at)
                 VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
              (user_id, paper.title, knowledge_json, summary, flaws, comparison, ppt_filename,
               now.isoformat(), expires.isoformat()))
    conn.commit()
    conn.close()

def get_user_papers(user_id: int) -> list[dict]:
    init_db()
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""SELECT id, title, summary, flaws, comparison, ppt_filename, timestamp 
                 FROM user_papers 
                 WHERE user_id = ? AND expires_at > ? 
                 ORDER BY timestamp DESC""",
              (user_id, datetime.now().isoformat()))
    rows = c.fetchall()
    conn.close()
    return [{"id": r[0], "title": r[1], "summary": r[2], "flaws": r[3], "comparison": r[4], 
             "ppt": r[5], "date": r[6]} for r in rows]

def cleanup_old_data():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("DELETE FROM user_papers WHERE expires_at < ?", (datetime.now().isoformat(),))
    conn.commit()
    conn.close()