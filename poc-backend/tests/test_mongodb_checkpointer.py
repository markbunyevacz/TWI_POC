"""Tests for MongoDB checkpointer – Cosmos DB-backed LangGraph state persistence."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


def _make_saver():
    """Create a MongoDBSaver with _get_db mocked so no real connection is needed."""
    with patch("app.agent.mongodb_checkpointer._get_db") as mock_db:
        fake_db = MagicMock()
        fake_db.__getitem__ = MagicMock(side_effect=lambda name: MagicMock())
        mock_db.return_value = fake_db
        from app.agent.mongodb_checkpointer import MongoDBSaver

        saver = MongoDBSaver()
    return saver


def _config(thread_id="conv-123", checkpoint_id=None, checkpoint_ns=""):
    """Build a minimal RunnableConfig."""
    cfg: dict = {"thread_id": thread_id, "checkpoint_ns": checkpoint_ns}
    if checkpoint_id:
        cfg["checkpoint_id"] = checkpoint_id
    return {"configurable": cfg}


class TestAgetTuple:
    @pytest.mark.asyncio
    async def test_returns_none_when_not_found(self):
        saver = _make_saver()
        saver.checkpoints.find_one = AsyncMock(return_value=None)

        result = await saver.aget_tuple(_config())
        assert result is None

    @pytest.mark.asyncio
    async def test_returns_tuple_for_latest_checkpoint(self):
        saver = _make_saver()

        checkpoint_data = {"id": "cp-1", "channel_versions": {}, "v": 1, "ts": "t"}
        ser_checkpoint = saver._ser(checkpoint_data)
        ser_metadata = saver._ser({"source": "input", "step": 0})

        saver.checkpoints.find_one = AsyncMock(
            return_value={
                "thread_id": "conv-123",
                "checkpoint_ns": "",
                "checkpoint_id": "cp-1",
                "checkpoint": ser_checkpoint,
                "metadata": ser_metadata,
                "blobs": {},
                "parent_checkpoint_id": None,
            }
        )
        saver.writes_collection.find = MagicMock(
            return_value=_async_cursor_mock([])
        )

        result = await saver.aget_tuple(_config())
        assert result is not None
        assert result.config["configurable"]["checkpoint_id"] == "cp-1"
        assert result.checkpoint["id"] == "cp-1"
        assert result.parent_config is None
        assert result.pending_writes == []

    @pytest.mark.asyncio
    async def test_returns_tuple_with_blobs_and_parent(self):
        saver = _make_saver()

        checkpoint_data = {"id": "cp-2", "channel_versions": {"messages": "1"}, "v": 1, "ts": "t"}
        ser_cp = saver._ser(checkpoint_data)
        ser_meta = saver._ser({"source": "loop", "step": 1})

        saver.checkpoints.find_one = AsyncMock(
            return_value={
                "thread_id": "conv-123",
                "checkpoint_ns": "",
                "checkpoint_id": "cp-2",
                "checkpoint": ser_cp,
                "metadata": ser_meta,
                "blobs": {"messages": saver._ser(["hello"])},
                "parent_checkpoint_id": "cp-1",
            }
        )
        saver.writes_collection.find = MagicMock(
            return_value=_async_cursor_mock([])
        )

        result = await saver.aget_tuple(_config())
        assert result is not None
        assert result.checkpoint["channel_values"]["messages"] == ["hello"]
        assert result.parent_config["configurable"]["checkpoint_id"] == "cp-1"

    @pytest.mark.asyncio
    async def test_returns_tuple_with_pending_writes(self):
        saver = _make_saver()

        ser_cp = saver._ser({"id": "cp-3", "channel_versions": {}, "v": 1, "ts": "t"})
        ser_meta = saver._ser({})

        saver.checkpoints.find_one = AsyncMock(
            return_value={
                "thread_id": "conv-123",
                "checkpoint_ns": "",
                "checkpoint_id": "cp-3",
                "checkpoint": ser_cp,
                "metadata": ser_meta,
                "blobs": {},
                "parent_checkpoint_id": None,
            }
        )
        saver.writes_collection.find = MagicMock(
            return_value=_async_cursor_mock(
                [
                    {
                        "task_id": "task-1",
                        "channel": "messages",
                        "value": saver._ser("pending-msg"),
                        "idx": 0,
                    }
                ]
            )
        )

        result = await saver.aget_tuple(_config())
        assert result is not None
        assert len(result.pending_writes) == 1
        assert result.pending_writes[0] == ("task-1", "messages", "pending-msg")


class TestAput:
    @pytest.mark.asyncio
    async def test_saves_checkpoint_and_returns_config(self):
        saver = _make_saver()
        saver.checkpoints.update_one = AsyncMock()

        config = _config(checkpoint_id="cp-parent")
        checkpoint = {
            "id": "cp-new",
            "v": 1,
            "ts": "t",
            "channel_versions": {"messages": "1"},
            "channel_values": {"messages": ["hi"]},
        }
        metadata = {"source": "loop", "step": 1}
        new_versions = {"messages": "1"}

        result = await saver.aput(config, checkpoint, metadata, new_versions)

        assert result["configurable"]["checkpoint_id"] == "cp-new"
        assert result["configurable"]["thread_id"] == "conv-123"
        saver.checkpoints.update_one.assert_called_once()
        call_args = saver.checkpoints.update_one.call_args
        assert call_args[1].get("upsert") is True


class TestAputWrites:
    @pytest.mark.asyncio
    async def test_stores_writes(self):
        saver = _make_saver()
        saver.writes_collection.update_one = AsyncMock()

        config = _config(checkpoint_id="cp-1")
        writes = [("messages", "hello"), ("intent", "generate")]

        await saver.aput_writes(config, writes, task_id="task-1")

        assert saver.writes_collection.update_one.call_count == 2


class TestAlist:
    @pytest.mark.asyncio
    async def test_yields_checkpoints(self):
        saver = _make_saver()

        ser_cp = saver._ser({"id": "cp-1", "channel_versions": {}, "v": 1, "ts": "t"})
        ser_meta = saver._ser({"source": "input", "step": 0})

        mock_cursor = _async_cursor_mock(
            [
                {
                    "thread_id": "conv-123",
                    "checkpoint_ns": "",
                    "checkpoint_id": "cp-1",
                    "checkpoint": ser_cp,
                    "metadata": ser_meta,
                    "blobs": {},
                    "parent_checkpoint_id": None,
                }
            ]
        )
        saver.checkpoints.find = MagicMock(return_value=_sortable_cursor(mock_cursor))
        saver.writes_collection.find = MagicMock(
            return_value=_async_cursor_mock([])
        )

        results = []
        async for item in saver.alist(_config()):
            results.append(item)

        assert len(results) == 1
        assert results[0].config["configurable"]["checkpoint_id"] == "cp-1"

    @pytest.mark.asyncio
    async def test_empty_when_no_checkpoints(self):
        saver = _make_saver()

        mock_cursor = _async_cursor_mock([])
        saver.checkpoints.find = MagicMock(return_value=_sortable_cursor(mock_cursor))

        results = []
        async for item in saver.alist(_config()):
            results.append(item)

        assert results == []


class TestGetNextVersion:
    def test_from_none(self):
        saver = _make_saver()
        v = saver.get_next_version(None, None)
        assert v.startswith("00000000000000000000000000000001.")

    def test_from_int(self):
        saver = _make_saver()
        v = saver.get_next_version(5, None)
        assert v.startswith("00000000000000000000000000000006.")

    def test_from_string(self):
        saver = _make_saver()
        v = saver.get_next_version("00000000000000000000000000000003.0.1234", None)
        assert v.startswith("00000000000000000000000000000004.")

    def test_monotonically_increasing(self):
        saver = _make_saver()
        v1 = saver.get_next_version(None, None)
        v2 = saver.get_next_version(v1, None)
        assert v2 > v1


class TestCreateCheckpointer:
    @pytest.mark.asyncio
    async def test_creates_and_indexes(self):
        with patch("app.agent.mongodb_checkpointer._get_db") as mock_db:
            fake_db = MagicMock()
            fake_db.__getitem__ = MagicMock(side_effect=lambda name: MagicMock())
            mock_db.return_value = fake_db

            with patch(
                "app.agent.mongodb_checkpointer.MongoDBSaver._ensure_indexes",
                new_callable=AsyncMock,
            ) as mock_idx:
                from app.agent.mongodb_checkpointer import create_mongodb_checkpointer

                saver = await create_mongodb_checkpointer()
                mock_idx.assert_called_once()
                assert saver is not None


# ---------------------------------------------------------------------------
# Async cursor helpers for mocking Motor cursors
# ---------------------------------------------------------------------------


class _AsyncCursorMock:
    """Minimal async-iterable mock that replays a list of documents."""

    def __init__(self, docs: list[dict]):
        self._docs = list(docs)
        self._idx = 0

    def sort(self, *_a, **_kw):
        return self

    def limit(self, *_a, **_kw):
        return self

    def __aiter__(self):
        self._idx = 0
        return self

    async def __anext__(self):
        if self._idx >= len(self._docs):
            raise StopAsyncIteration
        doc = self._docs[self._idx]
        self._idx += 1
        return doc


def _async_cursor_mock(docs: list[dict]) -> _AsyncCursorMock:
    return _AsyncCursorMock(docs)


def _sortable_cursor(cursor: _AsyncCursorMock) -> MagicMock:
    """Wrap an _AsyncCursorMock so that .find().sort().limit() chains work."""
    mock = MagicMock()
    mock.sort = MagicMock(return_value=cursor)
    return mock
