"""Pydantic model for the ``conversations`` Cosmos DB collection."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class Conversation(BaseModel):
    """Represents an active bot conversation tracked in Cosmos DB.

    TTL is enforced via a 90-day index on ``last_activity``.
    """

    conversation_id: str
    user_id: str
    tenant_id: str = "poc-tenant"
    channel: str = Field(
        ..., pattern=r"^(msteams|telegram)$", description="Bot channel identifier"
    )
    started_at: datetime
    last_activity: datetime
    message_count: int = 1
    status: str = "active"

    class Config:
        json_schema_extra = {
            "example": {
                "conversation_id": "19:abc123@thread.v2",
                "user_id": "aad-user-001",
                "tenant_id": "poc-tenant",
                "channel": "msteams",
                "started_at": "2026-03-12T08:00:00Z",
                "last_activity": "2026-03-12T08:05:00Z",
                "message_count": 3,
                "status": "active",
            }
        }


class ConversationCreate(BaseModel):
    """Payload accepted when creating/updating a conversation record."""

    conversation_id: str
    user_id: str
    tenant_id: str = "poc-tenant"
    channel: str = Field(..., pattern=r"^(msteams|telegram)$")
    started_at: Optional[datetime] = None
    last_activity: Optional[datetime] = None
