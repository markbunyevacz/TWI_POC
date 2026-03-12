"""Integration tests for the active MongoDBSaver checkpointer.

These tests require a running MongoDB-compatible instance (e.g. Cosmos DB
with the MongoDB API, or a local ``mongod``).  They are skipped by default
in CI unless the ``COSMOS_CONNECTION`` environment variable is set.

Run manually::

    COSMOS_CONNECTION="mongodb://localhost:27017/" pytest tests/test_checkpoint_integration.py -v
"""

import os
import uuid

import pytest
import pytest_asyncio

from langchain_core.runnables import RunnableConfig

pytestmark = pytest.mark.skipif(
    not os.getenv("COSMOS_CONNECTION"),
    reason="COSMOS_CONNECTION not set — skipping integration tests",
)


@pytest_asyncio.fixture
async def saver():
    """Create a MongoDBSaver that targets a disposable test collection."""
    from app.agent.mongodb_checkpointer import MongoDBSaver

    collection_name = f"test_checkpoints_{uuid.uuid4().hex[:8]}"
    s = MongoDBSaver(collection_name=collection_name)
    await s._ensure_indexes()
    yield s
    await s.collection.drop()


def _config(thread_id: str = "thread-1", checkpoint_id: str = "") -> RunnableConfig:
    configurable: dict = {"thread_id": thread_id}
    if checkpoint_id:
        configurable["checkpoint_id"] = checkpoint_id
    return RunnableConfig(configurable=configurable)


# ------------------------------------------------------------------
# Round-trip: put → get
# ------------------------------------------------------------------


@pytest.mark.asyncio
async def test_put_and_get(saver):
    """A checkpoint written with put should be retrievable via get."""
    checkpoint = {"id": "cp-1", "data": {"counter": 42}}
    channels = {}

    returned_config = await saver.put(_config("t1"), checkpoint, channels)

    assert returned_config["configurable"]["checkpoint_id"] == "cp-1"

    result = await saver.get(_config("t1", checkpoint_id="cp-1"))
    assert result is not None
    assert result["data"]["counter"] == 42


# ------------------------------------------------------------------
# get returns None for missing thread
# ------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_missing_thread(saver):
    """get returns None when no checkpoint exists for the thread."""
    result = await saver.get(_config("nonexistent"))
    assert result is None


# ------------------------------------------------------------------
# list ordering
# ------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_returns_newest_first(saver):
    """Checkpoints should be listed newest-first."""
    parent_id = ""
    for i in range(3):
        await saver.put(
            _config("t2", checkpoint_id=parent_id),
            {"id": f"cp-{i}", "step": i},
            {},
        )
        parent_id = f"cp-{i}"

    results = await saver.list(_config("t2"))
    assert len(results) >= 3
    assert results[0].checkpoint["step"] == 2
