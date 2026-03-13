"""MongoDB-backed LangGraph checkpointer for Cosmos DB with MongoDB API.

Implements the current BaseCheckpointSaver interface (aget_tuple, aput,
aput_writes, alist) so the graph can persist state across container restarts
and scale-out replicas.
"""

import base64
import logging
import random
from datetime import datetime, timezone
from typing import Any, AsyncIterator, Sequence

from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.base import (
    BaseCheckpointSaver,
    ChannelVersions,
    Checkpoint,
    CheckpointMetadata,
    CheckpointTuple,
)
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from pymongo import ASCENDING, DESCENDING

from app.config import settings

logger = logging.getLogger(__name__)

_client: AsyncIOMotorClient | None = None
_db: AsyncIOMotorDatabase | None = None


def _get_db() -> AsyncIOMotorDatabase:
    """Get or create the MongoDB client singleton."""
    global _client, _db
    if _db is None:
        _client = AsyncIOMotorClient(settings.cosmos_connection, retryWrites=False)
        _db = _client[settings.cosmos_database]
    return _db


class MongoDBSaver(BaseCheckpointSaver):
    """MongoDB-backed checkpoint saver for LangGraph using Cosmos DB (MongoDB API).

    Uses two collections:
      - ``agent_state``         – checkpoint data + serialised channel blobs
      - ``agent_state_writes``  – pending intermediate writes per task
    """

    def __init__(self, collection_name: str = "agent_state") -> None:
        super().__init__()
        db = _get_db()
        self.checkpoints = db[collection_name]
        self.writes_collection = db[f"{collection_name}_writes"]

    # ------------------------------------------------------------------
    # Serialisation helpers  (serde → base64-encoded dict for MongoDB)
    # ------------------------------------------------------------------

    def _ser(self, obj: Any) -> dict:
        type_str, data_bytes = self.serde.dumps_typed(obj)
        return {"type": type_str, "data": base64.b64encode(data_bytes).decode()}

    def _de(self, doc: dict) -> Any:
        return self.serde.loads_typed((doc["type"], base64.b64decode(doc["data"])))

    # ------------------------------------------------------------------
    # Index setup
    # ------------------------------------------------------------------

    async def _ensure_indexes(self) -> None:
        await self.checkpoints.create_index(
            [
                ("thread_id", ASCENDING),
                ("checkpoint_ns", ASCENDING),
                ("checkpoint_id", DESCENDING),
            ],
            unique=True,
            name="idx_thread_ns_checkpoint",
        )
        await self.writes_collection.create_index(
            [
                ("thread_id", ASCENDING),
                ("checkpoint_ns", ASCENDING),
                ("checkpoint_id", ASCENDING),
                ("task_id", ASCENDING),
                ("idx", ASCENDING),
            ],
            unique=True,
            name="idx_writes_lookup",
        )

    # ------------------------------------------------------------------
    # BaseCheckpointSaver interface
    # ------------------------------------------------------------------

    async def aget_tuple(self, config: RunnableConfig) -> CheckpointTuple | None:
        thread_id = config["configurable"]["thread_id"]
        checkpoint_ns = config["configurable"].get("checkpoint_ns", "")
        checkpoint_id = config["configurable"].get("checkpoint_id")

        if checkpoint_id:
            doc = await self.checkpoints.find_one(
                {
                    "thread_id": thread_id,
                    "checkpoint_ns": checkpoint_ns,
                    "checkpoint_id": checkpoint_id,
                }
            )
        else:
            doc = await self.checkpoints.find_one(
                {"thread_id": thread_id, "checkpoint_ns": checkpoint_ns},
                sort=[("checkpoint_id", DESCENDING)],
            )

        if not doc:
            return None

        checkpoint: Checkpoint = self._de(doc["checkpoint"])
        metadata: CheckpointMetadata = self._de(doc["metadata"])

        channel_values: dict[str, Any] = {}
        for key, blob in (doc.get("blobs") or {}).items():
            if blob.get("type") != "empty":
                channel_values[key] = self._de(blob)
        checkpoint["channel_values"] = channel_values

        pending_writes = await self._load_pending_writes(
            thread_id, checkpoint_ns, doc["checkpoint_id"]
        )

        parent_config = None
        if doc.get("parent_checkpoint_id"):
            parent_config = {
                "configurable": {
                    "thread_id": thread_id,
                    "checkpoint_ns": checkpoint_ns,
                    "checkpoint_id": doc["parent_checkpoint_id"],
                }
            }

        return CheckpointTuple(
            config={
                "configurable": {
                    "thread_id": thread_id,
                    "checkpoint_ns": checkpoint_ns,
                    "checkpoint_id": doc["checkpoint_id"],
                }
            },
            checkpoint=checkpoint,
            metadata=metadata,
            parent_config=parent_config,
            pending_writes=pending_writes,
        )

    async def aput(
        self,
        config: RunnableConfig,
        checkpoint: Checkpoint,
        metadata: CheckpointMetadata,
        new_versions: ChannelVersions,
    ) -> RunnableConfig:
        thread_id = config["configurable"]["thread_id"]
        checkpoint_ns = config["configurable"].get("checkpoint_ns", "")

        c = checkpoint.copy()
        channel_values: dict[str, Any] = c.pop("channel_values", {})

        blobs: dict[str, dict] = {}
        for k in channel_values:
            blobs[k] = self._ser(channel_values[k])

        doc = {
            "thread_id": thread_id,
            "checkpoint_ns": checkpoint_ns,
            "checkpoint_id": checkpoint["id"],
            "parent_checkpoint_id": config["configurable"].get("checkpoint_id"),
            "checkpoint": self._ser(c),
            "metadata": self._ser(metadata),
            "blobs": blobs,
            "created_at": datetime.now(timezone.utc),
        }

        await self.checkpoints.update_one(
            {
                "thread_id": thread_id,
                "checkpoint_ns": checkpoint_ns,
                "checkpoint_id": checkpoint["id"],
            },
            {"$set": doc},
            upsert=True,
        )

        return {
            "configurable": {
                "thread_id": thread_id,
                "checkpoint_ns": checkpoint_ns,
                "checkpoint_id": checkpoint["id"],
            }
        }

    async def aput_writes(
        self,
        config: RunnableConfig,
        writes: Sequence[tuple[str, Any]],
        task_id: str,
        task_path: str = "",
    ) -> None:
        thread_id = config["configurable"]["thread_id"]
        checkpoint_ns = config["configurable"].get("checkpoint_ns", "")
        checkpoint_id = config["configurable"]["checkpoint_id"]

        for idx, (channel, value) in enumerate(writes):
            doc = {
                "thread_id": thread_id,
                "checkpoint_ns": checkpoint_ns,
                "checkpoint_id": checkpoint_id,
                "task_id": task_id,
                "task_path": task_path,
                "idx": idx,
                "channel": channel,
                "value": self._ser(value),
            }
            await self.writes_collection.update_one(
                {
                    "thread_id": thread_id,
                    "checkpoint_ns": checkpoint_ns,
                    "checkpoint_id": checkpoint_id,
                    "task_id": task_id,
                    "idx": idx,
                },
                {"$set": doc},
                upsert=True,
            )

    async def alist(
        self,
        config: RunnableConfig | None,
        *,
        filter: dict[str, Any] | None = None,
        before: RunnableConfig | None = None,
        limit: int | None = None,
    ) -> AsyncIterator[CheckpointTuple]:
        query: dict[str, Any] = {}

        if config and "configurable" in config:
            query["thread_id"] = config["configurable"]["thread_id"]
            ns = config["configurable"].get("checkpoint_ns")
            if ns is not None:
                query["checkpoint_ns"] = ns

        if before and "configurable" in before:
            before_id = before["configurable"].get("checkpoint_id")
            if before_id:
                query["checkpoint_id"] = {"$lt": before_id}

        cursor = self.checkpoints.find(query).sort("checkpoint_id", DESCENDING)
        if limit is not None:
            cursor = cursor.limit(limit)

        async for doc in cursor:
            checkpoint: Checkpoint = self._de(doc["checkpoint"])
            metadata: CheckpointMetadata = self._de(doc["metadata"])

            if filter and not all(metadata.get(k) == v for k, v in filter.items()):
                continue

            channel_values: dict[str, Any] = {}
            for key, blob in (doc.get("blobs") or {}).items():
                if blob.get("type") != "empty":
                    channel_values[key] = self._de(blob)
            checkpoint["channel_values"] = channel_values

            tid = doc["thread_id"]
            cns = doc.get("checkpoint_ns", "")

            pending_writes = await self._load_pending_writes(
                tid, cns, doc["checkpoint_id"]
            )

            parent_config = None
            if doc.get("parent_checkpoint_id"):
                parent_config = {
                    "configurable": {
                        "thread_id": tid,
                        "checkpoint_ns": cns,
                        "checkpoint_id": doc["parent_checkpoint_id"],
                    }
                }

            yield CheckpointTuple(
                config={
                    "configurable": {
                        "thread_id": tid,
                        "checkpoint_ns": cns,
                        "checkpoint_id": doc["checkpoint_id"],
                    }
                },
                checkpoint=checkpoint,
                metadata=metadata,
                parent_config=parent_config,
                pending_writes=pending_writes,
            )

    def get_next_version(self, current: str | int | None, channel: None) -> str:
        """Return a monotonically increasing string version identifier."""
        if current is None:
            current_v = 0
        elif isinstance(current, int):
            current_v = current
        else:
            current_v = int(current.split(".")[0])
        next_v = current_v + 1
        next_h = random.random()
        return f"{next_v:032}.{next_h:016}"

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _load_pending_writes(
        self, thread_id: str, checkpoint_ns: str, checkpoint_id: str
    ) -> list[tuple[str, str, Any]]:
        """Load pending writes for a given checkpoint as PendingWrite tuples."""
        writes: list[tuple[str, str, Any]] = []
        cursor = self.writes_collection.find(
            {
                "thread_id": thread_id,
                "checkpoint_ns": checkpoint_ns,
                "checkpoint_id": checkpoint_id,
            }
        ).sort("idx", ASCENDING)
        async for doc in cursor:
            writes.append((doc["task_id"], doc["channel"], self._de(doc["value"])))
        return writes


async def create_mongodb_checkpointer() -> MongoDBSaver:
    """Factory function to create and initialize the MongoDB checkpointer."""
    saver = MongoDBSaver()
    await saver._ensure_indexes()
    logger.info("MongoDB checkpointer initialized")
    return saver
