import os
from google.cloud import storage

# Path to the service account JSON, assuming it's in the project root
CREDENTIALS_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
    "maxwelll-502103-58e3c6ccff0d.json",
)
BUCKET_NAME = "maxwell-clothing"

# Module-level singleton — client is created once on first use and reused for
# all subsequent requests. Avoids reading the credentials file from disk on
# every upload call.
_storage_client = None


def get_storage_client() -> storage.Client:
    global _storage_client
    if _storage_client is None:
        if not os.path.exists(CREDENTIALS_PATH):
            raise FileNotFoundError(
                f"Google Cloud credentials not found at {CREDENTIALS_PATH}"
            )
        _storage_client = storage.Client.from_service_account_json(CREDENTIALS_PATH)
    return _storage_client


def upload_file_to_gcs(file_obj, filename: str, content_type: str) -> str:
    """Uploads a file to Google Cloud Storage and returns the public URL."""
    import uuid

    client = get_storage_client()
    bucket = client.bucket(BUCKET_NAME)

    # Create a unique filename to prevent overwrites
    ext = filename.split(".")[-1] if "." in filename else ""
    unique_filename = (
        f"challans/{uuid.uuid4().hex}.{ext}" if ext else f"challans/{uuid.uuid4().hex}"
    )

    blob = bucket.blob(unique_filename)
    blob.upload_from_file(file_obj, content_type=content_type)

    # Since Uniform Bucket-Level Access is enabled on the bucket,
    # we cannot use ACLs (make_public).
    # Ensure the bucket itself has "Storage Object Viewer" for "allUsers"
    # in GCP Console if you want public access.
    return blob.public_url
