"""Tests for MongoDB checkpointer - Cosmos DB-backed LangGraph state persistence."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone


class TestMongoDBSaver:
    """Tests for the MongoDB checkpointer."""

    @pytest.mark.asyncio
    async def test_get_returns_none_when_no_thread_id(self):
        """Test that get returns None when thread_id is missing from config."""
        from app.agent.mongodb_checkpointer import MongoDBSaver
        
        saver = MongoDBSaver()
        saver.collection = MagicMock()
        
        config = {}  # No configurable key
        result = await saver.get(config)
        
        assert result is None

    @pytest.mark.asyncio
    async def test_get_returns_checkpoint_when_found(self):
        """Test that get returns checkpoint when found in database."""
        from app.agent.mongodb_checkpointer import MongoDBSaver
        
        saver = MongoDBSaver()
        
        # Mock the collection
        mock_collection = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.__aiter__ = AsyncMock(return_value=iter([
            {
                "thread_id": "conv-123",
                "checkpoint_id": "checkpoint-1",
                "checkpoint": {"id": "checkpoint-1", "values": {"test": "data"}},
            }
        ]))
        mock_collection.find_one = AsyncMock(return_value={
            "thread_id": "conv-123",
            "checkpoint_id": "checkpoint-1", 
            "checkpoint": {"id": "checkpoint-1", "values": {"test": "data"}},
        })
        saver.collection = mock_collection
        
        config = {"configurable": {"thread_id": "conv-123", "checkpoint_id": "checkpoint-1"}}
        result = await saver.get(config)
        
        assert result is not None
        assert "id" in result

    @pytest.mark.asyncio
    async def test_put_saves_checkpoint(self):
        """Test that put saves checkpoint to database."""
        from app.agent.mongodb_checkpointer import MongoDBSaver
        
        saver = MongoDBSaver()
        
        # Mock the collection
        mock_collection = MagicMock()
        mock_collection.update_one = AsyncMock()
        saver.collection = mock_collection
        
        config = {"configurable": {"thread_id": "conv-123"}}
        checkpoint = {"id": "checkpoint-1", "values": {"test": "data"}}
        channels = {}
        
        result = await saver.put(config, checkpoint, channels)
        
        # Verify update_one was called with upsert=True
        mock_collection.update_one.assert_called_once()
        call_kwargs = mock_collection.update_one.call_args[1]
        assert call_kwargs.get("upsert") is True

    @pytest.mark.asyncio
    async def test_put_requires_thread_id(self):
        """Test that put raises ValueError when thread_id is missing."""
        from app.agent.mongodb_checkpointer import MongoDBSaver
        
        saver = MongoDBSaver()
        saver.collection = MagicMock()
        
        config = {}  # No thread_id
        checkpoint = {"id": "checkpoint-1"}
        channels = {}
        
        with pytest.raises(ValueError, match="thread_id is required"):
            await saver.put(config, checkpoint, channels)

    @pytest.mark.asyncio
    async def test_list_returns_empty_when_no_thread_id(self):
        """Test that list returns empty when thread_id is missing."""
        from app.agent.mongodb_checkpointer import MongoDBSaver
        
        saver = MongoDBSaver()
        saver.collection = MagicMock()
        
        config = {}  # No thread_id
        result = await saver.list(config)
        
        assert result == []

    @pytest.mark.asyncio
    async def test_get_next_version_returns_increment(self):
        """Test that get_next_version returns an incrementing version."""
        from app.agent.mongodb_checkpointer import MongoDBSaver
        
        saver = MongoDBSaver()
        
        # Should return 1 (not 0) for first version
        version = await saver.get_next_version(None, ["channel1"])
        assert version == 1

    @pytest.mark.asyncio
    async def test_get_writes_returns_empty_list(self):
        """Test that get_writes returns empty list (not implemented for PoC)."""
        from app.agent.mongodb_checkpointer import MongoDBSaver
        
        saver = MongoDBSaver()
        saver.collection = MagicMock()
        
        config = {"configurable": {"thread_id": "conv-123"}}
        result = await saver.get_writes(config)
        
        assert result == []


class TestCreateCheckpointer:
    """Tests for the checkpointer factory function."""

    @pytest.mark.asyncio
    async def test_create_mongodb_checkpointer_initializes(self):
        """Test that factory creates and initializes checkpointer."""
        with patch("app.agent.mongodb_checkpointer._get_db") as mock_get_db:
            with patch("app.agent.mongodb_checkpointer.MongoDBSaver") as MockSaver:
                mock_saver_instance = AsyncMock()
                mock_saver_instance._ensure_indexes = AsyncMock()
                MockSaver.return_value = mock_saver_instance
                
                from app.agent.mongodb_checkpointer import create_mongodb_checkpointer
                
                result = await create_mongodb_checkpointer()
                
                mock_saver_instance._ensure_indexes.assert_called_once()
