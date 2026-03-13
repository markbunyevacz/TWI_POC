"""Tests for MongoDB checkpointer - Cosmos DB-backed LangGraph state persistence."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


def _make_saver():
    """Create a MongoDBSaver with _get_db mocked so no real connection is needed."""
    with patch("app.agent.mongodb_checkpointer._get_db") as mock_db:
        mock_db.return_value = {"agent_state": MagicMock()}
        from app.agent.mongodb_checkpointer import MongoDBSaver

        saver = MongoDBSaver()
    return saver


class TestMongoDBSaver:
    """Tests for the MongoDB checkpointer."""

    @pytest.mark.asyncio
    async def test_get_returns_none_when_no_thread_id(self):
        saver = _make_saver()
        saver.collection = MagicMock()

        result = await saver.get({})
        assert result is None

    @pytest.mark.asyncio
    async def test_get_returns_checkpoint_when_found(self):
        saver = _make_saver()

        mock_collection = MagicMock()
        mock_collection.find_one = AsyncMock(
            return_value={
                "thread_id": "conv-123",
                "checkpoint_id": "checkpoint-1",
                "checkpoint": {"id": "checkpoint-1", "values": {"test": "data"}},
            }
        )
        saver.collection = mock_collection

        config = {
            "configurable": {"thread_id": "conv-123", "checkpoint_id": "checkpoint-1"}
        }
        result = await saver.get(config)

        assert result is not None
        assert "id" in result

    @pytest.mark.asyncio
    async def test_put_saves_checkpoint(self):
        saver = _make_saver()

        mock_collection = MagicMock()
        mock_collection.update_one = AsyncMock()
        saver.collection = mock_collection

        config = {"configurable": {"thread_id": "conv-123"}}
        checkpoint = {"id": "checkpoint-1", "values": {"test": "data"}}

        await saver.put(config, checkpoint, {})

        mock_collection.update_one.assert_called_once()
        call_kwargs = mock_collection.update_one.call_args[1]
        assert call_kwargs.get("upsert") is True

    @pytest.mark.asyncio
    async def test_put_requires_thread_id(self):
        saver = _make_saver()
        saver.collection = MagicMock()

        with pytest.raises(ValueError, match="thread_id is required"):
            await saver.put({}, {"id": "checkpoint-1"}, {})

    @pytest.mark.asyncio
    async def test_list_returns_empty_when_no_thread_id(self):
        saver = _make_saver()
        saver.collection = MagicMock()

        result = await saver.list({})
        assert result == []

    @pytest.mark.asyncio
    async def test_get_next_version_returns_increment(self):
        saver = _make_saver()

        version = await saver.get_next_version(None, ["channel1"])
        assert version == 1

    @pytest.mark.asyncio
    async def test_get_writes_returns_empty_list(self):
        saver = _make_saver()
        saver.collection = MagicMock()

        config = {"configurable": {"thread_id": "conv-123"}}
        result = await saver.get_writes(config)
        assert result == []


class TestCreateCheckpointer:
    @pytest.mark.asyncio
    async def test_create_mongodb_checkpointer_initializes(self):
        with patch("app.agent.mongodb_checkpointer._get_db"):
            with patch("app.agent.mongodb_checkpointer.MongoDBSaver") as MockSaver:
                mock_saver_instance = AsyncMock()
                mock_saver_instance._ensure_indexes = AsyncMock()
                MockSaver.return_value = mock_saver_instance

                from app.agent.mongodb_checkpointer import create_mongodb_checkpointer

                await create_mongodb_checkpointer()

                mock_saver_instance._ensure_indexes.assert_called_once()
