"""MongoDB-backed LangGraph checkpointer for Cosmos DB with MongoDB API.

This provides persistent checkpointing so graph state survives container restarts
and multiple replicas can share state.
"""

import json
import logging
from datetime import datetime, timezone
from typing import Any, Sequence

from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.base import (
    BaseCheckpointSaver,
    Checkpoint,
    CheckpointTuple,
    ChannelVersions,
    PendingWrite,
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
        _client = AsyncIOMotorClient(settings.cosmos_connection)
        _db = _client[settings.cosmos_database]
    return _db


class MongoDBSaver(BaseCheckpointSaver):
    """MongoDB-backed checkpoint saver for LangGraph using Cosmos DB (MongoDB API).
    
    This implements the BaseCheckpointSaver interface required by LangGraph
    for persistent state management across container restarts and scale-out.
    """

    def __init__(self, collection_name: str = "agent_state") -> None:
        """Initialize the MongoDB checkpointer."""
        self.collection = _get_db()[collection_name]
    
    async def _ensure_indexes(self) -> None:
        """Create indexes for efficient checkpoint queries."""
        await self.collection.create_index(
            [("thread_id", ASCENDING), ("checkpoint_id", ASCENDING)],
            unique=True,
            name="idx_thread_checkpoint"
        )
        await self.collection.create_index(
            [("thread_id", ASCENDING), ("created_at", DESCENDING)],
            name="idx_thread_created"
        )

    async def get(self, config: RunnableConfig) -> Checkpoint | None:
        """Retrieve a checkpoint by config."""
        thread_id = config.get("configurable", {}).get("thread_id")
        checkpoint_id = config.get("configurable", {}).get("checkpoint_id")
        
        if not thread_id:
            return None
            
        query = {"thread_id": thread_id}
        if checkpoint_id:
            query["checkpoint_id"] = checkpoint_id
        else:
            # Get latest checkpoint if no checkpoint_id specified
            doc = await self.collection.find_one(
                {"thread_id": thread_id},
                sort=[("created_at", DESCENDING)]
            )
            if doc:
                return self._doc_to_checkpoint(doc)
            return None
        
        doc = await self.collection.find_one(query)
        if doc:
            return self._doc_to_checkpoint(doc)
        return None

    async def get_next_version(
        self, parent_version: str | None, channel_names: Sequence[str]
    ) -> int:
        """Get the next version number for a channel."""
        # Simple incrementing version - could be improved with atomic operations
        return 1

    async def put(
        self,
        config: RunnableConfig,
        checkpoint: Checkpoint,
        channels: ChannelVersions,
    ) -> RunnableConfig:
        """Save a checkpoint to MongoDB."""
        thread_id = config.get("configurable", {}).get("thread_id")
        if not thread_id:
            raise ValueError("thread_id is required in config")
        
        checkpoint_id = checkpoint.get("id")
        
        doc = {
            "thread_id": thread_id,
            "checkpoint_id": checkpoint_id,
            "checkpoint": checkpoint,
            "channels": channels,
            "created_at": datetime.now(timezone.utc),
            "parent_checkpoint_id": config.get("configurable", {}).get("checkpoint_id"),
        }
        
        await self.collection.update_one(
            {"thread_id": thread_id, "checkpoint_id": checkpoint_id},
            {"$set": doc},
            upsert=True
        )
        
        return {
            "configurable": {
                **config.get("configurable", {}),
                "checkpoint_id": checkpoint_id,
            }
        }

    async def list(
        self,
        config: RunnableConfig,
        *,
        limit: int = 10,
        before: RunnableConfig | None = None,
    ) -> Sequence[CheckpointTuple]:
        """List checkpoints for a thread."""
        thread_id = config.get("configurable", {}).get("thread_id")
        if not thread_id:
            return []
        
        query = {"thread_id": thread_id}
        
        if before:
            before_checkpoint_id = before.get("configurable", {}).get("checkpoint_id")
            if before_checkpoint_id:
                query["checkpoint_id"] = {"$lt": before_checkpoint_id}
        
        cursor = self.collection.find(query).sort("created_at", DESCENDING).limit(limit)
        
        checkpoints = []
        async for doc in cursor:
            # Get parent checkpoint
            parent_config = None
            if doc.get("parent_checkpoint_id"):
                parent_doc = await self.collection.find_one({
                    "thread_id": thread_id,
                    "checkpoint_id": doc["parent_checkpoint_id"]
                })
                if parent_doc:
                    parent_config = {
                        "configurable": {
                            "thread_id": thread_id,
                            "checkpoint_id": parent_doc["checkpoint_id"]
                        }
                    }
            
            checkpoints.append(CheckpointTuple(
                config={
                    "configurable": {
                        "thread_id": thread_id,
                        "checkpoint_id": doc["checkpoint_id"]
                    }
                },
                checkpoint=self._doc_to_checkpoint(doc),
                parent_config=parent_config,
                metadata=doc.get("metadata", {})
            ))
        
        return checkpoints

    async def get_writes(
        self,
        config: RunnableConfig,
    ) -> Sequence[PendingWrite]:
        """Get pending writes for a checkpoint."""
        # For PoC, we don't implement pending writes - they are typically
        # used for async operations. Could be extended in the future.
        return []

    def _doc_to_checkpoint(self, doc: dict) -> Checkpoint:
        """Convert a MongoDB document to a Checkpoint."""
        checkpoint = doc.get("checkpoint", {})
        
        # Ensure the checkpoint has an id
        if "id" not in checkpoint:
            checkpoint["id"] = doc.get("checkpoint_id", "")
        
        return checkpoint


async def create_mongodb_checkpointer() -> MongoDBSaver:
    """Factory function to create and initialize the MongoDB checkpointer."""
    saver = MongoDBSaver()
    await saver._ensure_indexes()
    logger.info("MongoDB checkpointer initialized")
    return saver
