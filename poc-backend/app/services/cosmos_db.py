import logging
from datetime import datetime, timezone

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from app.config import settings

logger = logging.getLogger(__name__)

_client: AsyncIOMotorClient | None = None
_db: AsyncIOMotorDatabase | None = None


def _get_db() -> AsyncIOMotorDatabase:
    """Return a singleton Motor database handle.

    Raises:
        RuntimeError: If ``cosmos_connection`` is not configured.
    """
    global _client, _db
    if _db is None:
        if not settings.cosmos_connection:
            raise RuntimeError(
                "COSMOS_CONNECTION is not configured. "
                "Set the cosmos_connection setting or the COSMOS_CONNECTION env var."
            )
        try:
            _client = AsyncIOMotorClient(settings.cosmos_connection)
            _db = _client[settings.cosmos_database]
        except Exception as exc:
            logger.error("Failed to connect to Cosmos DB: %s", exc)
            raise
    return _db


class ConversationStore:
    def __init__(self) -> None:
        self._collection = None

    @property
    def collection(self):
        if self._collection is None:
            self._collection = _get_db()["conversations"]
        return self._collection

    async def get_or_create(
        self,
        conversation_id: str,
        user_id: str,
        channel: str,
        tenant_id: str = "",
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

    async def update_status(self, conversation_id: str, status: str) -> None:
        """Update the status field of an existing conversation."""
        await self.collection.update_one(
            {"conversation_id": conversation_id},
            {
                "$set": {
                    "status": status,
                    "last_activity": datetime.now(timezone.utc),
                },
            },
        )


class AuditStore:
    def __init__(self) -> None:
        self._collection = None

    @property
    def collection(self):
        if self._collection is None:
            self._collection = _get_db()["audit_log"]
        return self._collection

    async def log(self, entry: dict) -> None:
        entry["created_at"] = datetime.now(timezone.utc)
        await self.collection.insert_one(entry)
        logger.info("Audit log entry saved: conversation_id=%s", entry.get("conversation_id"))


class DocumentStore:
    def __init__(self) -> None:
        self._collection = None

    @property
    def collection(self):
        if self._collection is None:
            self._collection = _get_db()["generated_documents"]
        return self._collection

    async def save(self, doc: dict) -> dict:
        doc["created_at"] = datetime.now(timezone.utc)
        await self.collection.insert_one(doc)
        return doc

    async def find_by_id(self, document_id: str) -> dict | None:
        """Return a single document by its ``document_id``."""
        return await self.collection.find_one({"document_id": document_id})

    async def list_documents(
        self,
        user_id: str | None = None,
        tenant_id: str | None = None,
        limit: int = 50,
        skip: int = 0,
    ) -> list[dict]:
        """Return documents, newest first, with optional user/tenant filter."""
        query: dict = {}
        if user_id:
            query["user_id"] = user_id
        if tenant_id:
            query["tenant_id"] = tenant_id
        cursor = (
            self.collection.find(query)
            .sort("created_at", -1)
            .skip(skip)
            .limit(limit)
        )
        results: list[dict] = []
        async for doc in cursor:
            doc.pop("_id", None)
            results.append(doc)
        return results

    async def search(self, title_query: str, limit: int = 20) -> list[dict]:
        """Search documents by title (case-insensitive substring match)."""
        cursor = (
            self.collection.find(
                {"title": {"$regex": title_query, "$options": "i"}}
            )
            .sort("created_at", -1)
            .limit(limit)
        )
        results: list[dict] = []
        async for doc in cursor:
            doc.pop("_id", None)
            results.append(doc)
        return results
