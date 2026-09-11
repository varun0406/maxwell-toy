import os
from google.cloud import storage
import uuid

# Path to the service account JSON, assuming it's in the project root
CREDENTIALS_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "maxwelll-502103-58e3c6ccff0d.json")
BUCKET_NAME = "maxwell-clothing"

def get_storage_client():
    if not os.path.exists(CREDENTIALS_PATH):
        raise FileNotFoundError(f"Google Cloud credentials not found at {CREDENTIALS_PATH}")
    return storage.Client.from_service_account_json(CREDENTIALS_PATH)

def upload_file_to_gcs(file_obj, filename: str, content_type: str) -> str:
    """Uploads a file to Google Cloud Storage and returns the public URL."""
    client = get_storage_client()
    bucket = client.bucket(BUCKET_NAME)
    
    # Create a unique filename to prevent overwrites
    ext = filename.split('.')[-1] if '.' in filename else ''
    unique_filename = f"challans/{uuid.uuid4().hex}.{ext}" if ext else f"challans/{uuid.uuid4().hex}"
    
    blob = bucket.blob(unique_filename)
    blob.upload_from_file(file_obj, content_type=content_type)
    
    # Make the blob publicly viewable (optional, but needed for a simple URL approach)
    # Alternatively, you can use signed URLs if it should be private.
    blob.make_public()
    
    return blob.public_url
