"""Pydantic model for the ``generated_documents`` Cosmos DB collection."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class TWIDocument(BaseModel):
    """A generated TWI document stored alongside its PDF in Blob Storage."""

    document_id: str = Field(..., description="Unique hex identifier (uuid4)")
    conversation_id: str
    user_id: str
    tenant_id: str = "poc-tenant"
    title: str
    content_type: str = "twi"
    draft_content: str = Field(..., description="Final approved markdown content")
    pdf_blob_name: str = Field(
        ..., description="Blob path: twi/{conversation_id}/{uuid}.pdf"
    )
    pdf_url: Optional[str] = Field(None, description="SAS URL with 24h expiry")
    llm_model: str = "gpt-4o"
    revision_count: int = 0
    status: str = "approved"
    approved_at: str = Field(..., description="ISO 8601 UTC timestamp")
    approved_by: str
    created_at: Optional[datetime] = None

    class Config:
        json_schema_extra = {
            "example": {
                "document_id": "a1b2c3d4e5f6",
                "conversation_id": "conv-001",
                "user_id": "aad-user-001",
                "tenant_id": "poc-tenant",
                "title": "CNC-01 gép napi beállítása",
                "content_type": "twi",
                "draft_content": "## CÍM: CNC-01 gép napi beállítása ...",
                "pdf_blob_name": "twi/conv-001/a1b2c3d4.pdf",
                "pdf_url": "https://storage.blob.core.windows.net/...",
                "llm_model": "gpt-4o",
                "revision_count": 1,
                "status": "approved",
                "approved_at": "2026-03-12T08:10:00Z",
                "approved_by": "aad-user-001",
            }
        }
