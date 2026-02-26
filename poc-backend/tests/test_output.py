import pytest
from unittest.mock import AsyncMock, patch

from app.agent.nodes.output import output_node

@pytest.mark.asyncio
async def test_output_node_saves_to_document_store():
    state = {
        "conversation_id": "conv-123",
        "user_id": "test-user",
        "tenant_id": "test-tenant",
        "draft": "# TWI Cím\nIde jön a szöveg",
        "draft_metadata": {"model": "test-model", "revision": 1},
        "revision_count": 1,
        "approval_timestamp": "2026-02-26T12:00:00Z"
    }

    with patch("app.agent.nodes.output.generate_twi_pdf", new_callable=AsyncMock) as mock_generate_pdf, \
         patch("app.agent.nodes.output.upload_pdf", new_callable=AsyncMock) as mock_upload_pdf, \
         patch("app.agent.nodes.output.DocumentStore") as mock_document_store_class:
        
        mock_generate_pdf.return_value = b"fake-pdf-bytes"
        mock_upload_pdf.return_value = "https://fake.url/blob.pdf"
        
        mock_store_instance = mock_document_store_class.return_value
        mock_store_instance.save = AsyncMock()
        
        result = await output_node(state)
        
        # Verify PDF generation was called
        mock_generate_pdf.assert_called_once()
        
        # Verify Blob Storage upload was called
        mock_upload_pdf.assert_called_once()
        
        # Verify DocumentStore was instantiated and save was called
        mock_document_store_class.assert_called_once()
        mock_store_instance.save.assert_called_once()
        
        # Verify the saved document structure
        saved_doc = mock_store_instance.save.call_args[0][0]
        assert saved_doc["conversation_id"] == "conv-123"
        assert saved_doc["user_id"] == "test-user"
        assert saved_doc["title"] == "TWI Cím"
        assert saved_doc["content_type"] == "twi"
        assert saved_doc["pdf_url"] == "https://fake.url/blob.pdf"
        assert saved_doc["status"] == "approved"
        assert saved_doc["llm_model"] == "test-model"
        assert saved_doc["revision_count"] == 1
        assert "document_id" in saved_doc
        assert saved_doc["approved_by"] == "test-user"
        
        # Verify the returned state
        assert result["status"] == "completed"
        assert result["pdf_url"] == "https://fake.url/blob.pdf"
        assert result["title"] == "TWI Cím"
