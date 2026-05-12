import os
import json
import hashlib
from datetime import datetime, timedelta
from typing import List, Dict
import psycopg2
from psycopg2.extras import RealDictCursor
from knowledge.schema import PaperKnowledge

class NeonDB:
    def __init__(self):
        self.conn = psycopg2.connect(os.getenv("NEON_DATABASE_URL"))
        self.create_tables()

    def create_tables(self):
        with self.conn.cursor() as cur:
            cur.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id SERIAL PRIMARY KEY,
                    username TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                
                CREATE TABLE IF NOT EXISTS user_papers (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER REFERENCES users(id),
                    title TEXT NOT NULL,
                    knowledge_json TEXT NOT NULL,
                    summary TEXT,
                    flaws TEXT,
                    comparison TEXT,
                    ppt_filename TEXT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    expires_at TIMESTAMP NOT NULL
                );
            ''')
            self.conn.commit()

    def hash_password(self, password: str) -> str:
        return hashlib.sha256(password.encode()).hexdigest()

    def signup(self, username: str, password: str) -> bool:
        try:
            with self.conn.cursor() as cur:
                cur.execute("INSERT INTO users (username, password_hash) VALUES (%s, %s)",
                           (username, self.hash_password(password)))
                self.conn.commit()
                return True
        except:
            return False

    def login(self, username: str, password: str) -> dict | None:
        with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT id, username FROM users WHERE username = %s AND password_hash = %s",
                       (username, self.hash_password(password)))
            return cur.fetchone()

    def save_paper(self, user_id: int, paper: PaperKnowledge, summary: str, flaws: str, comparison: str, ppt_filename: str) -> int:
        expires = datetime.now() + timedelta(days=10)
        with self.conn.cursor() as cur:
            cur.execute('''
                INSERT INTO user_papers 
                (user_id, title, knowledge_json, summary, flaws, comparison, ppt_filename, expires_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            ''', (user_id, paper.title, json.dumps(paper.model_dump()), summary, flaws, comparison, ppt_filename, expires))
            paper_id = cur.fetchone()[0]
            self.conn.commit()
            return paper_id

    def get_user_papers(self, user_id: int) -> List[dict]:
        with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT id, title, summary, flaws, comparison, ppt_filename, timestamp 
                FROM user_papers 
                WHERE user_id = %s AND expires_at > NOW() 
                ORDER BY timestamp DESC
            """, (user_id,))
            return cur.fetchall()

    def get_paper_by_id(self, paper_id: int, user_id: int):
        with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                "SELECT id, title, knowledge_json, summary, flaws, comparison, ppt_filename, timestamp "
                "FROM user_papers "
                "WHERE id = %s AND user_id = %s AND expires_at > NOW()",
                (paper_id, user_id)
            )
            row = cur.fetchone()
            return dict(row) if row else None

    def cleanup_old_data(self):
        with self.conn.cursor() as cur:
            cur.execute("DELETE FROM user_papers WHERE expires_at < NOW()")
            self.conn.commit()

    def self_destruct_old_papers(self):
        """Delete old papers and their S3 files after 10 days"""
        with self.conn.cursor() as cur:
            cur.execute("SELECT title FROM user_papers WHERE expires_at < NOW()")
            old_papers = cur.fetchall()
            for (title,) in old_papers:
                from s3_cache import delete_from_s3
                delete_from_s3(title)
            cur.execute("DELETE FROM user_papers WHERE expires_at < NOW()")
            self.conn.commit()


# Create single DB instance
_db = NeonDB()

# Expose functions
def init_db():
    return _db

def signup(username, password):
    return _db.signup(username, password)

def login(username, password):
    return _db.login(username, password)

def save_paper(user_id, paper, summary, flaws, comparison, ppt_filename) -> int:
    return _db.save_paper(user_id, paper, summary, flaws, comparison, ppt_filename)

def get_user_papers(user_id):
    return _db.get_user_papers(user_id)

def get_paper_by_id(paper_id, user_id):
    return _db.get_paper_by_id(paper_id, user_id)