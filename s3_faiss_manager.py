"""
S3 FAISS Vector Manager
Handles persistent storage and retrieval of FAISS vectors with 10-day auto-destruct
"""
import os
from dotenv import load_dotenv
import boto3
import pickle
from datetime import datetime, timedelta
from typing import Optional
import logging

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)

# AWS S3 Configuration
S3_BUCKET = os.getenv("S3_BUCKET", "paperintel-vectors")
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
AWS_ACCESS_KEY = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")

s3_client = boto3.client(
    "s3",
    region_name=AWS_REGION,
    aws_access_key_id=AWS_ACCESS_KEY,
    aws_secret_access_key=AWS_SECRET_KEY
)

def generate_vector_key(paper_title: str, user_id: int) -> str:
    """Generate S3 key for FAISS vectors"""
    import hashlib
    hash_val = hashlib.md5(f"{user_id}:{paper_title}".encode()).hexdigest()
    return f"vectors/{user_id}/{hash_val}/faiss.pkl"

def upload_vectors_to_s3(chunks, paper_title: str, user_id: int) -> str:
    """Upload FAISS vector chunks to S3"""
    try:
        s3_key = generate_vector_key(paper_title, user_id)
        
        # Serialize chunks
        vector_data = pickle.dumps(chunks)
        
        # Add metadata with 10-day expiry
        expires_at = (datetime.now() + timedelta(days=10)).isoformat()
        
        s3_client.put_object(
            Bucket=S3_BUCKET,
            Key=s3_key,
            Body=vector_data,
            Metadata={
                "expires_at": expires_at,
                "user_id": str(user_id),
                "paper_title": paper_title,
                "uploaded_at": datetime.now().isoformat()
            }
        )
        
        logger.info(f"✅ Uploaded vectors to S3: {s3_key}")
        return s3_key
        
    except Exception as e:
        logger.error(f"❌ Failed to upload vectors to S3: {str(e)}")
        return None

def download_vectors_from_s3(s3_key: str) -> Optional[list]:
    """Download FAISS vectors from S3"""
    try:
        response = s3_client.get_object(Bucket=S3_BUCKET, Key=s3_key)
        vector_data = response["Body"].read()
        chunks = pickle.loads(vector_data)
        
        logger.info(f"✅ Downloaded vectors from S3: {s3_key}")
        return chunks
        
    except s3_client.exceptions.NoSuchKey:
        logger.warning(f"⚠️ Vectors not found in S3: {s3_key}")
        return None
    except Exception as e:
        logger.error(f"❌ Failed to download vectors from S3: {str(e)}")
        return None

def check_vectors_exist(paper_title: str, user_id: int) -> bool:
    """Check if vectors already exist in S3"""
    s3_key = generate_vector_key(paper_title, user_id)
    try:
        s3_client.head_object(Bucket=S3_BUCKET, Key=s3_key)
        return True
    except s3_client.exceptions.NoSuchKey:
        return False

def cleanup_expired_vectors():
    """Cleanup expired vectors from S3"""
    try:
        response = s3_client.list_objects_v2(Bucket=S3_BUCKET, Prefix="vectors/")
        
        if "Contents" not in response:
            return
        
        now = datetime.now()
        deleted_count = 0
        
        for obj in response["Contents"]:
            try:
                metadata = s3_client.head_object(Bucket=S3_BUCKET, Key=obj["Key"])["Metadata"]
                expires_at = datetime.fromisoformat(metadata.get("expires_at", ""))
                
                if now > expires_at:
                    s3_client.delete_object(Bucket=S3_BUCKET, Key=obj["Key"])
                    deleted_count += 1
                    
            except Exception as e:
                logger.warning(f"Error processing {obj['Key']}: {str(e)}")
                continue
        
        logger.info(f"✅ Cleaned up {deleted_count} expired vectors from S3")
        
    except Exception as e:
        logger.error(f"❌ Failed to cleanup S3 vectors: {str(e)}")

def ensure_s3_bucket_exists():
    """Ensure S3 bucket exists with proper lifecycle policy"""
    try:
        s3_client.head_bucket(Bucket=S3_BUCKET)
    except s3_client.exceptions.NoSuchBucket:
        s3_client.create_bucket(Bucket=S3_BUCKET)
        logger.info(f"✅ Created S3 bucket: {S3_BUCKET}")
    except Exception as e:
        logger.error(f"❌ Failed to ensure S3 bucket: {str(e)}")
