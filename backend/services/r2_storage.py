import boto3
from botocore.exceptions import ClientError
from config import settings
import io

def get_r2_client():
    return boto3.client(
        "s3",
        endpoint_url=settings.R2_ENDPOINT_URL,
        aws_access_key_id=settings.R2_ACCESS_KEY_ID,
        aws_secret_access_key=settings.R2_SECRET_ACCESS_KEY,
        region_name="auto",
    )

def upload_file(file_bytes: bytes, key: str, content_type: str = "application/octet-stream") -> str:
    client = get_r2_client()
    client.put_object(
        Bucket=settings.R2_BUCKET_NAME,
        Key=key,
        Body=file_bytes,
        ContentType=content_type,
    )
    return key

def download_file(key: str) -> bytes:
    client = get_r2_client()
    response = client.get_object(Bucket=settings.R2_BUCKET_NAME, Key=key)
    return response["Body"].read()

def delete_file(key: str):
    client = get_r2_client()
    client.delete_object(Bucket=settings.R2_BUCKET_NAME, Key=key)

def generate_presigned_url(key: str, expiry: int = 3600) -> str:
    client = get_r2_client()
    try:
        url = client.generate_presigned_url(
            "get_object",
            Params={"Bucket": settings.R2_BUCKET_NAME, "Key": key},
            ExpiresIn=expiry,
        )
        return url
    except ClientError:
        return f"{settings.R2_PUBLIC_DOMAIN}/{key}"
