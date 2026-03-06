"""Integration test stubs for MongoDBSaver checkpointer.

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

# Skip the entire module when no database is available.
pytestmark = pytest.mark.skipif(
    not os.getenv("COSMOS_CONNECTION"),
    reason="COSMOS_CONNECTION not set — skipping integration tests",
)


@pytest_asyncio.fixture
async def saver():
    """Create a MongoDBSaver that targets a disposable test collection."""
    # Import here so the module-level skip takes effect first.
    from app.services.checkpoint import MongoDBSaver

    collection_name = f"test_checkpoints_{uuid.uuid4().hex[:8]}"
    s = MongoDBSaver(collection_name=collection_name, ttl_seconds=300)
    await s.ensure_indexes()
    yield s
    # Cleanup: drop the temporary collection after each test.
    await s.collection.drop()


def _config(thread_id: str = "thread-1", checkpoint_id: str = "") -> RunnableConfig:
    cfg: dict = {"configurable": {"thread_id": thread_id}}
    if checkpoint_id:
        cfg["configurable"]["checkpoint_id"] = checkpoint_id
    return cfg


# ------------------------------------------------------------------
# Round-trip: put → get
# ------------------------------------------------------------------


@pytest.mark.asyncio
async def test_put_and_get_tuple(saver):
    """A checkpoint written with aput should be retrievable via aget_tuple."""
    checkpoint = {"id": "cp-1", "data": {"counter": 42}}
    metadata = {"source": "test", "step": 1}

    returned_config = await saver.aput(_config("t1"), checkpoint, metadata)

    assert returned_config["configurable"]["checkpoint_id"] == "cp-1"

    result = await saver.aget_tuple(_config("t1"))
    assert result is not None
    assert result.checkpoint["data"]["counter"] == 42
    assert result.metadata["source"] == "test"


# ------------------------------------------------------------------
# aget_tuple returns None for missing thread
# ------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_tuple_missing_thread(saver):
    """aget_tuple returns None when no checkpoint exists for the thread."""
    result = await saver.aget_tuple(_config("nonexistent"))
    assert result is None


# ------------------------------------------------------------------
# alist ordering
# ------------------------------------------------------------------


@pytest.mark.asyncio
async def test_alist_returns_newest_first(saver):
    """Checkpoints should be listed newest-first."""
    for i in range(3):
        await saver.aput(
            _config("t2", checkpoint_id=f"cp-prev-{i}" if i else ""),
            {"id": f"cp-{i}", "step": i},
            {"step": i},
        )

    results = await saver.alist(_config("t2"))
    assert len(results) == 3
    # Newest (highest step) should come first.
    assert results[0].checkpoint["step"] == 2


# ------------------------------------------------------------------
# pending_writes round-trip
# ------------------------------------------------------------------


@pytest.mark.asyncio
async def test_pending_writes_persisted(saver):
    """Writes stored with aput_writes should appear in aget_tuple."""
    checkpoint = {"id": "cp-pw", "data": {}}
    await saver.aput(_config("t3"), checkpoint, {})

    await saver.aput_writes(
        _config("t3", checkpoint_id="cp-pw"),
        [("channel_a", {"msg": "hello"})],
        task_id="task-1",
    )

    result = await saver.aget_tuple(_config("t3"))
    assert result is not None
    assert len(result.pending_writes) == 1
    task_id, channel, value = result.pending_writes[0]
    assert task_id == "task-1"
    assert channel == "channel_a"
    assert value == {"msg": "hello"}
