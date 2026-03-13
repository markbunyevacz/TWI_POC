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
        if not settings.cosmos_connection:
            raise RuntimeError(
                "Cosmos DB connection string not configured. "
                "Set COSMOS_CONNECTION environment variable."
            )
        _client = AsyncIOMotorClient(settings.cosmos_connection, retryWrites=False)
        _db = _client[settings.cosmos_database]
    return _db


class ConversationStore:
    def __init__(self) -> None:
        try:
            self.collection = _get_db()["conversations"]
        except RuntimeError:
            logger.warning(
                "Cosmos DB not configured — ConversationStore disabled. "
                "Conversations will NOT be tracked."
            )
            self.collection = None

    async def get_or_create(
        self,
        conversation_id: str,
        user_id: str,
        channel: str,
        tenant_id: str | None = None,
    ) -> dict:
        if self.collection is None:
            logger.warning(
                "ConversationStore.get_or_create() called without DB — "
                "returning empty dict for conversation_id=%s",
                conversation_id,
            )
            return {}

        resolved_tenant = tenant_id or settings.default_tenant_id
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
            "tenant_id": resolved_tenant,
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
        try:
            self.collection = _get_db()["audit_log"]
        except RuntimeError:
            logger.warning(
                "Cosmos DB not configured — AuditStore disabled. "
                "EU AI Act audit trail will NOT be persisted!"
            )
            self.collection = None

    async def log(self, entry: dict) -> None:
        if self.collection is None:
            logger.error(
                "AUDIT TRAIL SKIPPED (EU AI Act compliance gap): "
                "event_type=%s conversation_id=%s — Cosmos DB not available.",
                entry.get("event_type", "unknown"),
                entry.get("conversation_id", "unknown"),
            )
            return
        entry["created_at"] = datetime.now(timezone.utc)
        await self.collection.insert_one(entry)
        logger.info(
            "Audit log entry saved: conversation_id=%s", entry.get("conversation_id")
        )


class DocumentStore:
    def __init__(self) -> None:
        try:
            self.collection = _get_db()["generated_documents"]
        except RuntimeError:
            logger.warning(
                "Cosmos DB not configured — DocumentStore disabled. "
                "Generated documents will NOT be persisted."
            )
            self.collection = None

    async def save(self, doc: dict) -> dict:
        if self.collection is None:
            logger.warning(
                "DocumentStore.save() called without DB — document NOT persisted: "
                "conversation_id=%s",
                doc.get("conversation_id", "unknown"),
            )
            return doc
        doc["created_at"] = datetime.now(timezone.utc)
        await self.collection.insert_one(doc)
        return doc


class PendingStateStore:
    """Lightweight key-value store for transient per-conversation flags.

    Used to track Telegram pending-revision state across replicas.
    Falls back to an in-memory dict when Cosmos DB is not available.
    """

    def __init__(self) -> None:
        self._memory: dict[str, bool] = {}
        try:
            self.collection = _get_db()["pending_state"]
        except RuntimeError:
            logger.warning(
                "Cosmos DB not configured — PendingStateStore using in-memory fallback. "
                "State will NOT survive restarts or scale across replicas."
            )
            self.collection = None

    async def set_flag(self, conversation_id: str, flag: str) -> None:
        if self.collection is None:
            self._memory[f"{conversation_id}:{flag}"] = True
            return
        try:
            await self.collection.update_one(
                {"conversation_id": conversation_id, "flag": flag},
                {
                    "$set": {
                        "conversation_id": conversation_id,
                        "flag": flag,
                        "value": True,
                        "updated_at": datetime.now(timezone.utc),
                    }
                },
                upsert=True,
            )
        except Exception as exc:
            logger.warning("PendingStateStore.set_flag DB error, using memory: %s", exc)
            self._memory[f"{conversation_id}:{flag}"] = True

    async def pop_flag(self, conversation_id: str, flag: str) -> bool:
        """Check and atomically remove a flag. Returns True if it was set."""
        if self.collection is None:
            return self._memory.pop(f"{conversation_id}:{flag}", False)
        try:
            doc = await self.collection.find_one_and_delete(
                {"conversation_id": conversation_id, "flag": flag}
            )
            return doc is not None
        except Exception as exc:
            logger.warning("PendingStateStore.pop_flag DB error, using memory: %s", exc)
            return self._memory.pop(f"{conversation_id}:{flag}", False)
