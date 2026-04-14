"""
Cache Manager
Redis-based caching for paper queries
"""
import os
from dotenv import load_dotenv
import redis
import json
import hashlib
import logging
from typing import Optional

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)

# Redis Configuration
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
REDIS_DB = int(os.getenv("REDIS_DB", 0))
CACHE_TTL = 3600  # 1 hour

try:
    redis_client = redis.Redis(
        host=REDIS_HOST,
        port=REDIS_PORT,
        db=REDIS_DB,
        decode_responses=True
    )
    redis_client.ping()
    logger.info("✅ Connected to Redis")
except Exception as e:
    logger.error(f"❌ Failed to connect to Redis: {str(e)}")
    redis_client = None

def get_cache_key(paper_title: str, query: str) -> str:
    """Generate cache key"""
    key = f"paper:{paper_title}:query:{query}"
    return hashlib.md5(key.encode()).hexdigest()

def make_serializable(obj):
    """Recursively convert objects to JSON-serializable dicts"""
    if isinstance(obj, (str, int, float, bool, type(None))):
        return obj
    elif isinstance(obj, list):
        return [make_serializable(item) for item in obj]
    elif isinstance(obj, dict):
        return {k: make_serializable(v) for k, v in obj.items()}
    elif hasattr(obj, '__dict__'):
        if obj.__class__.__name__ == "PaperKnowledge":
            return {
                "__type__": "PaperKnowledge",
                **{k: make_serializable(v) for k, v in obj.__dict__.items()}
            }
        return {k: make_serializable(v) for k, v in obj.__dict__.items()}
    return str(obj)

def get_cached_response(paper_title: str, query: str) -> Optional[dict]:
    """Retrieve cached response"""
    if not redis_client:
        return None
    
    try:
        key = get_cache_key(paper_title, query)
        data = redis_client.get(key)
        
        if data:
            return json.loads(data)
    except Exception as e:
        logger.warning(f"⚠️ Cache retrieval failed: {str(e)}")
    
    return None

def cache_response(paper_title: str, query: str, result: dict, ttl: int = CACHE_TTL):
    """Cache response with TTL"""
    if not redis_client:
        return
    
    try:
        key = get_cache_key(paper_title, query)
        serializable_result = make_serializable(result)
        redis_client.setex(key, ttl, json.dumps(serializable_result))
        logger.info(f"✅ Cached response for: {paper_title[:30]}...")
    except Exception as e:
        logger.warning(f"⚠️ Cache write failed: {str(e)}")

def clear_cache_for_paper(paper_title: str):
    """Clear all cache entries for a paper"""
    if not redis_client:
        return
    
    try:
        pattern = f"paper:{paper_title}:query:*"
        keys = redis_client.keys(pattern)
        
        if keys:
            redis_client.delete(*keys)
            logger.info(f"✅ Cleared cache for: {paper_title}")
    except Exception as e:
        logger.warning(f"⚠️ Cache clear failed: {str(e)}")

def health_check() -> bool:
    """Check Redis connection"""
    if not redis_client:
        return False
    
    try:
        redis_client.ping()
        return True
    except Exception:
        return False
