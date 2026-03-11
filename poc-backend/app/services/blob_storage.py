import logging
import asyncio
from datetime import datetime, timezone, timedelta

from azure.storage.blob import (
    BlobServiceClient,
    ContentSettings,
    generate_blob_sas,
    BlobSasPermissions,
)

from app.config import settings

logger = logging.getLogger(__name__)

_client: BlobServiceClient | None = None


def _get_client() -> BlobServiceClient:
    global _client
    if _client is None:
        _client = BlobServiceClient.from_connection_string(settings.blob_connection)
    return _client


async def upload_pdf(pdf_bytes: bytes, blob_name: str) -> str:
    """Upload PDF bytes to Blob Storage and return a 24-hour SAS URL."""
    client = _get_client()
    container_client = client.get_container_client(settings.blob_container)
    blob_client = container_client.get_blob_client(blob_name)

    await asyncio.to_thread(
        blob_client.upload_blob,
        data=pdf_bytes,
        overwrite=True,
        content_settings=ContentSettings(content_type="application/pdf"),
    )
    logger.info("PDF uploaded: blob_name=%s", blob_name)

    account_name: str = client.account_name or ""

    # The account_key is only available when the client was created from a
    # connection string.  When using managed identity or SAS-based auth the
    # credential object will not expose ``account_key``.
    try:
        account_key = client.credential.account_key
    except AttributeError as exc:
        raise RuntimeError(
            "Cannot generate SAS URL: BlobServiceClient credential does not "
            "expose an account_key.  Ensure BLOB_CONNECTION uses a connection "
            "string that includes the account key."
        ) from exc

    sas_token = generate_blob_sas(
        account_name=account_name,
        container_name=settings.blob_container,
        blob_name=blob_name,
        account_key=account_key,
        permission=BlobSasPermissions(read=True),
        expiry=datetime.now(timezone.utc) + timedelta(hours=24),
    )

    return f"{blob_client.url}?{sas_token}"


async def refresh_sas_url(blob_name: str, expiry_hours: int = 24) -> str:
    """Generate a fresh SAS URL for an existing blob.

    This is used when a previously issued SAS URL has expired and the
    user needs to re-download the PDF.
    """
    client = _get_client()
    container_client = client.get_container_client(settings.blob_container)
    blob_client = container_client.get_blob_client(blob_name)

    account_name: str = client.account_name or ""

    try:
        account_key = client.credential.account_key
    except AttributeError as exc:
        raise RuntimeError(
            "Cannot generate SAS URL: BlobServiceClient credential does not "
            "expose an account_key."
        ) from exc

    sas_token = generate_blob_sas(
        account_name=account_name,
        container_name=settings.blob_container,
        blob_name=blob_name,
        account_key=account_key,
        permission=BlobSasPermissions(read=True),
        expiry=datetime.now(timezone.utc) + timedelta(hours=expiry_hours),
    )

    return f"{blob_client.url}?{sas_token}"
