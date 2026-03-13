"""Pydantic model for the ``audit_log`` Cosmos DB collection (EU AI Act)."""

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field, model_validator

AuditEventType = Literal[
    "twi_generated",
    "twi_approved",
    "twi_rejected",
    "twi_revised",
]


def _default_tenant_id() -> str:
    from app.config import settings

    return settings.default_tenant_id


class AuditEntry(BaseModel):
    """Immutable audit log entry written for every significant workflow event.

    Required by EU AI Act for traceability of AI-generated content.
    """

    conversation_id: str
    user_id: str
    tenant_id: str = Field(default=None)
    channel: str = Field(..., pattern=r"^(msteams|telegram)$")
    event_type: AuditEventType
    intent: Optional[str] = None
    llm_model: Optional[str] = None
    llm_tokens_used: Optional[int] = Field(
        None, ge=0, description="Total tokens consumed (prompt + completion)"
    )
    revision_count: int = 0
    pdf_blob_name: Optional[str] = None
    status: str
    approval_timestamp: Optional[str] = None
    created_at: Optional[datetime] = None

    @model_validator(mode="before")
    @classmethod
    def _set_tenant_default(cls, values: dict) -> dict:
        if not values.get("tenant_id"):
            values["tenant_id"] = _default_tenant_id()
        return values

    class Config:
        json_schema_extra = {
            "example": {
                "conversation_id": "conv-001",
                "user_id": "aad-user-001",
                "tenant_id": "my-tenant",
                "channel": "msteams",
                "event_type": "twi_generated",
                "intent": "generate_twi",
                "llm_model": "gpt-4o",
                "llm_tokens_used": 2450,
                "revision_count": 0,
                "pdf_blob_name": "twi/conv-001/a1b2c3d4.pdf",
                "status": "completed",
                "approval_timestamp": "2026-03-12T08:10:00Z",
            }
        }
