import redis
import json
import hashlib
from config import GROQ_API_KEY

redis_client = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)

def get_cache_key(paper_title: str, query: str) -> str:
    key = f"{paper_title}:{query}"
    return hashlib.md5(key.encode()).hexdigest()

def cache_response(paper_title: str, query: str, response: dict, ttl=3600):
    key = get_cache_key(paper_title, query)
    redis_client.setex(key, ttl, json.dumps(response))

def get_cached_response(paper_title: str, query: str):
    key = get_cache_key(paper_title, query)
    data = redis_client.get(key)
    return json.loads(data) if data else None