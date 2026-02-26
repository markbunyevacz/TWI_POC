import logging
from datetime import datetime, timezone

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from app.config import settings

logger = logging.getLogger(__name__)

_client: AsyncIOMotorClient | None = None
_db: AsyncIOMotorDatabase | None = None


def _get_db() -> AsyncIOMotorDatabase:
    global _client, _db
    if _db is None:
        _client = AsyncIOMotorClient(settings.cosmos_connection)
        _db = _client[settings.cosmos_database]
    return _db


class ConversationStore:
    def __init__(self) -> None:
        self.collection = _get_db()["conversations"]

    async def get_or_create(
        self,
        conversation_id: str,
        user_id: str,
        channel: str,
        tenant_id: str = "poc-tenant",
    ) -> dict:
        doc = await self.collection.find_one({"conversation_id": conversation_id})
        if doc:
            await self.collection.update_one(
                {"conversation_id": conversation_id},
                {
                    "$set": {"last_activity": datetime.now(timezone.utc)},
                    "$inc": {"message_count": 1},
                },
            )
            return doc

        new_doc: dict = {
            "conversation_id": conversation_id,
            "user_id": user_id,
            "tenant_id": tenant_id,
            "channel": channel,
            "started_at": datetime.now(timezone.utc),
            "last_activity": datetime.now(timezone.utc),
            "message_count": 1,
            "status": "active",
        }
        await self.collection.insert_one(new_doc)
        return new_doc


class AuditStore:
    def __init__(self) -> None:
        self.collection = _get_db()["audit_log"]

    async def log(self, entry: dict) -> None:
        entry["created_at"] = datetime.now(timezone.utc)
        await self.collection.insert_one(entry)
        logger.info("Audit log entry saved: conversation_id=%s", entry.get("conversation_id"))


class DocumentStore:
    def __init__(self) -> None:
        self.collection = _get_db()["generated_documents"]

    async def save(self, doc: dict) -> dict:
        doc["created_at"] = datetime.now(timezone.utc)
        await self.collection.insert_one(doc)
        return doc
