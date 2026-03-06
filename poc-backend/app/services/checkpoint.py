"""Cosmos DB (MongoDB API) backed checkpointer for LangGraph.

Replaces the in-memory MemorySaver so that graph state survives container
restarts and works across multiple replicas.  Uses the ``agent_state``
collection that is already provisioned by the Bicep template.
"""

import logging
from datetime import datetime, timezone
from typing import Any, Optional, Sequence

from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.base import (
    BaseCheckpointSaver,
    Checkpoint,
    CheckpointMetadata,
    CheckpointTuple,
)

from app.services.cosmos_db import _get_db

logger = logging.getLogger(__name__)


class MongoDBSaver(BaseCheckpointSaver):
    """Persist LangGraph checkpoints in Cosmos DB (MongoDB API).

    The collection schema mirrors the indexes defined in ``main.bicep``::

        - thread_id   (partition key equivalent)
        - checkpoint_id
        - created_at
    """

    def __init__(self, collection_name: str = "agent_state") -> None:
        super().__init__()
        db = _get_db()
        self.collection = db[collection_name]

    # ------------------------------------------------------------------
    # Read
    # ------------------------------------------------------------------

    async def aget_tuple(self, config: RunnableConfig) -> Optional[CheckpointTuple]:
        """Return the latest checkpoint for the given thread."""
        thread_id = config["configurable"]["thread_id"]
        doc = await self.collection.find_one(
            {"thread_id": thread_id},
            sort=[("created_at", -1)],
        )
        if doc is None:
            return None

        checkpoint = doc["checkpoint"]
        metadata = doc.get("metadata", {})
        parent_config = doc.get("parent_config")

        pending_writes = [
            (pw["task_id"], pw["channel"], pw["value"])
            for pw in doc.get("pending_writes", [])
        ]

        return CheckpointTuple(
            config={
                "configurable": {
                    "thread_id": thread_id,
                    "checkpoint_id": doc["checkpoint_id"],
                },
            },
            checkpoint=checkpoint,
            metadata=metadata,
            parent_config=parent_config,
            pending_writes=pending_writes,
        )

    async def alist(
        self,
        config: Optional[RunnableConfig],
        *,
        filter: Optional[dict[str, Any]] = None,
        before: Optional[RunnableConfig] = None,
        limit: Optional[int] = None,
    ) -> list[CheckpointTuple]:
        """List checkpoints, newest first."""
        query: dict[str, Any] = {}
        if config and "configurable" in config:
            thread_id = config["configurable"].get("thread_id")
            if thread_id:
                query["thread_id"] = thread_id
        if before and "configurable" in before:
            before_id = before["configurable"].get("checkpoint_id")
            if before_id:
                query["checkpoint_id"] = {"$lt": before_id}

        cursor = self.collection.find(query).sort("created_at", -1)
        if limit:
            cursor = cursor.limit(limit)

        results: list[CheckpointTuple] = []
        async for doc in cursor:
            pending_writes = [
                (pw["task_id"], pw["channel"], pw["value"])
                for pw in doc.get("pending_writes", [])
            ]
            results.append(
                CheckpointTuple(
                    config={
                        "configurable": {
                            "thread_id": doc["thread_id"],
                            "checkpoint_id": doc["checkpoint_id"],
                        },
                    },
                    checkpoint=doc["checkpoint"],
                    metadata=doc.get("metadata", {}),
                    parent_config=doc.get("parent_config"),
                    pending_writes=pending_writes,
                )
            )
        return results

    # ------------------------------------------------------------------
    # Write
    # ------------------------------------------------------------------

    async def aput(
        self,
        config: RunnableConfig,
        checkpoint: Checkpoint,
        metadata: CheckpointMetadata,
        new_versions: Optional[dict[str, Any]] = None,
    ) -> RunnableConfig:
        """Persist a checkpoint."""
        thread_id = config["configurable"]["thread_id"]
        checkpoint_id = checkpoint["id"]

        doc = {
            "thread_id": thread_id,
            "checkpoint_id": checkpoint_id,
            "checkpoint": checkpoint,
            "metadata": metadata,
            "created_at": datetime.now(timezone.utc),
        }

        parent_id = config["configurable"].get("checkpoint_id")
        if parent_id:
            doc["parent_config"] = {
                "configurable": {
                    "thread_id": thread_id,
                    "checkpoint_id": parent_id,
                },
            }

        await self.collection.update_one(
            {"thread_id": thread_id, "checkpoint_id": checkpoint_id},
            {"$set": doc},
            upsert=True,
        )
        logger.debug(
            "Checkpoint saved: thread_id=%s checkpoint_id=%s",
            thread_id,
            checkpoint_id,
        )

        return {
            "configurable": {
                "thread_id": thread_id,
                "checkpoint_id": checkpoint_id,
            },
        }

    async def aput_writes(
        self,
        config: RunnableConfig,
        writes: Sequence[tuple[str, Any]],
        task_id: str,
    ) -> None:
        """Persist intermediate writes (pending sends / channel updates)."""
        thread_id = config["configurable"]["thread_id"]
        checkpoint_id = config["configurable"].get("checkpoint_id", "")

        await self.collection.update_one(
            {"thread_id": thread_id, "checkpoint_id": checkpoint_id},
            {
                "$push": {
                    "pending_writes": {
                        "$each": [
                            {"task_id": task_id, "channel": ch, "value": val}
                            for ch, val in writes
                        ],
                    },
                },
            },
            upsert=True,
        )

    # ------------------------------------------------------------------
    # Sync wrappers (not used in this async app, but required by ABC)
    # ------------------------------------------------------------------

    def get_tuple(self, config: RunnableConfig) -> Optional[CheckpointTuple]:
        raise NotImplementedError("Use aget_tuple — this app is fully async.")

    def list(
        self,
        config: Optional[RunnableConfig],
        *,
        filter: Optional[dict[str, Any]] = None,
        before: Optional[RunnableConfig] = None,
        limit: Optional[int] = None,
    ) -> list[CheckpointTuple]:
        raise NotImplementedError("Use alist — this app is fully async.")

    def put(
        self,
        config: RunnableConfig,
        checkpoint: Checkpoint,
        metadata: CheckpointMetadata,
        new_versions: Optional[dict[str, Any]] = None,
    ) -> RunnableConfig:
        raise NotImplementedError("Use aput — this app is fully async.")

    def put_writes(
        self,
        config: RunnableConfig,
        writes: Sequence[tuple[str, Any]],
        task_id: str,
    ) -> None:
        raise NotImplementedError("Use aput_writes — this app is fully async.")
