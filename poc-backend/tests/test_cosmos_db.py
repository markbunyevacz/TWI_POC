import pytest
from unittest.mock import AsyncMock, patch

from app.services.cosmos_db import DocumentStore, ConversationStore, AuditStore

@pytest.mark.asyncio
async def test_document_store_save():
    with patch("app.services.cosmos_db._get_db") as mock_get_db:
        mock_collection = AsyncMock()
        mock_get_db.return_value = {"generated_documents": mock_collection}

        store = DocumentStore()
        
        doc_to_save = {"title": "Test Doc", "content": "Content"}
        result = await store.save(doc_to_save)
        
        mock_collection.insert_one.assert_called_once()
        saved_doc = mock_collection.insert_one.call_args[0][0]
        
        assert saved_doc["title"] == "Test Doc"
        assert saved_doc["content"] == "Content"
        assert "created_at" in saved_doc
        assert result == saved_doc
