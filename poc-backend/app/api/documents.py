"""Document management API — list, search, and re-download past documents."""

import logging

from fastapi import APIRouter, HTTPException, Query

from app.services.cosmos_db import DocumentStore
from app.services.blob_storage import refresh_sas_url

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/documents", tags=["documents"])

_store = DocumentStore()


@router.get("")
async def list_documents(
    user_id: str | None = Query(None, description="Filter by user ID"),
    tenant_id: str | None = Query(None, description="Filter by tenant ID"),
    limit: int = Query(50, ge=1, le=200),
    skip: int = Query(0, ge=0),
) -> list[dict]:
    """List documents, newest first, with optional user/tenant filter."""
    try:
        return await _store.list_documents(
            user_id=user_id, tenant_id=tenant_id, limit=limit, skip=skip
        )
    except Exception as exc:
        logger.error("Failed to list documents: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to list documents.") from exc


@router.get("/search")
async def search_documents(
    q: str = Query(..., min_length=1, description="Title search query"),
    limit: int = Query(20, ge=1, le=100),
) -> list[dict]:
    """Search documents by title (case-insensitive substring match)."""
    try:
        return await _store.search(title_query=q, limit=limit)
    except Exception as exc:
        logger.error("Document search failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Search failed.") from exc


@router.get("/{document_id}")
async def get_document(document_id: str) -> dict:
    """Retrieve a single document by its ID."""
    try:
        doc = await _store.find_by_id(document_id)
    except Exception as exc:
        logger.error("Failed to fetch document %s: %s", document_id, exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to fetch document.") from exc
    if doc is None:
        raise HTTPException(status_code=404, detail="Document not found.")
    doc.pop("_id", None)
    return doc


@router.post("/{document_id}/refresh-url")
async def refresh_document_url(document_id: str) -> dict:
    """Generate a fresh 24-hour SAS URL for a document's PDF.

    Use this when the original download URL has expired.
    """
    try:
        doc = await _store.find_by_id(document_id)
    except Exception as exc:
        logger.error("Failed to fetch document %s: %s", document_id, exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to fetch document.") from exc

    if doc is None:
        raise HTTPException(status_code=404, detail="Document not found.")

    blob_name = doc.get("pdf_blob_name")
    if not blob_name:
        raise HTTPException(
            status_code=400, detail="Document has no associated PDF blob."
        )

    try:
        new_url = await refresh_sas_url(blob_name)
    except Exception as exc:
        logger.error("Failed to refresh SAS URL: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=500, detail="Failed to generate new download URL."
        ) from exc

    return {"document_id": document_id, "pdf_url": new_url}
