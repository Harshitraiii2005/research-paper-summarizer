import boto3
import pickle
import hashlib
from pathlib import Path
from config import AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_REGION, S3_BUCKET_NAME

s3 = boto3.client(
    's3',
    aws_access_key_id=AWS_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
    region_name=AWS_REGION
)

def get_s3_key(paper_title: str):
    return f"faiss_vectors/{hashlib.md5(paper_title.encode()).hexdigest()}.pkl"

def save_to_s3(paper_title: str, data: dict):
    key = get_s3_key(paper_title)
    s3.put_object(Bucket=S3_BUCKET_NAME, Key=key, Body=pickle.dumps(data))

def load_from_s3(paper_title: str):
    try:
        key = get_s3_key(paper_title)
        response = s3.get_object(Bucket=S3_BUCKET_NAME, Key=key)
        return pickle.loads(response['Body'].read())
    except:
        return None

def delete_from_s3(paper_title: str):
    try:
        key = get_s3_key(paper_title)
        s3.delete_object(Bucket=S3_BUCKET_NAME, Key=key)
    except:
        pass