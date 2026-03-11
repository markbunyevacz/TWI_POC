"""Tests for the output_node: full pipeline, partial failures, and error paths."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from app.agent.nodes.output import output_node


_BASE_STATE = {
    "conversation_id": "conv-123",
    "user_id": "test-user",
    "tenant_id": "test-tenant",
    "draft": "# TWI Cím\nIde jön a szöveg",
    "draft_metadata": {"model": "test-model", "revision": 1},
    "revision_count": 1,
    "approval_timestamp": "2026-02-26T12:00:00Z",
}


def _make_mock_store() -> MagicMock:
    mock = MagicMock()
    mock.save = AsyncMock()
    return mock


# ---------------------------------------------------------------------------
# Happy-path: full pipeline (generate → upload → save)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_output_node_saves_to_document_store():
    mock_store = _make_mock_store()

    with patch("app.agent.nodes.output.generate_twi_pdf", new_callable=AsyncMock) as mock_gen, \
         patch("app.agent.nodes.output.upload_pdf", new_callable=AsyncMock) as mock_upload, \
         patch("app.agent.nodes.output._doc_store", mock_store):

        mock_gen.return_value = b"fake-pdf-bytes"
        mock_upload.return_value = "https://fake.url/blob.pdf"

        result = await output_node(dict(_BASE_STATE))

        mock_gen.assert_called_once()
        mock_upload.assert_called_once()
        mock_store.save.assert_called_once()

        saved_doc = mock_store.save.call_args[0][0]
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

        assert result["status"] == "completed"
        assert result["pdf_url"] == "https://fake.url/blob.pdf"
        assert result["title"] == "TWI Cím"


# ---------------------------------------------------------------------------
# Error path: PDF generation fails → status="error"
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_output_node_pdf_generation_failure():
    mock_store = _make_mock_store()

    with patch("app.agent.nodes.output.generate_twi_pdf", new_callable=AsyncMock) as mock_gen, \
         patch("app.agent.nodes.output.upload_pdf", new_callable=AsyncMock) as mock_upload, \
         patch("app.agent.nodes.output._doc_store", mock_store):

        mock_gen.side_effect = RuntimeError("WeasyPrint crash")

        result = await output_node(dict(_BASE_STATE))

        assert result["status"] == "error"
        mock_upload.assert_not_called()
        mock_store.save.assert_not_called()


# ---------------------------------------------------------------------------
# Error path: Blob upload fails → status="error"
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_output_node_upload_failure():
    mock_store = _make_mock_store()

    with patch("app.agent.nodes.output.generate_twi_pdf", new_callable=AsyncMock) as mock_gen, \
         patch("app.agent.nodes.output.upload_pdf", new_callable=AsyncMock) as mock_upload, \
         patch("app.agent.nodes.output._doc_store", mock_store):

        mock_gen.return_value = b"fake-pdf-bytes"
        mock_upload.side_effect = RuntimeError("Blob connection failed")

        result = await output_node(dict(_BASE_STATE))

        assert result["status"] == "error"
        mock_store.save.assert_not_called()


# ---------------------------------------------------------------------------
# Partial failure: DB save fails but PDF URL is preserved
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_output_node_db_save_failure_preserves_pdf_url():
    mock_store = _make_mock_store()
    mock_store.save.side_effect = RuntimeError("Cosmos DB unavailable")

    with patch("app.agent.nodes.output.generate_twi_pdf", new_callable=AsyncMock) as mock_gen, \
         patch("app.agent.nodes.output.upload_pdf", new_callable=AsyncMock) as mock_upload, \
         patch("app.agent.nodes.output._doc_store", mock_store):

        mock_gen.return_value = b"fake-pdf-bytes"
        mock_upload.return_value = "https://fake.url/blob.pdf"

        result = await output_node(dict(_BASE_STATE))

        # PDF was uploaded successfully — status should still be "completed"
        assert result["status"] == "completed"
        assert result["pdf_url"] == "https://fake.url/blob.pdf"
        mock_store.save.assert_called_once()


# ---------------------------------------------------------------------------
# Edge case: missing optional fields in state
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_output_node_missing_optional_fields():
    mock_store = _make_mock_store()
    minimal_state = {
        "conversation_id": "conv-min",
        "user_id": "user-min",
        "draft": "Simple draft",
    }

    with patch("app.agent.nodes.output.generate_twi_pdf", new_callable=AsyncMock) as mock_gen, \
         patch("app.agent.nodes.output.upload_pdf", new_callable=AsyncMock) as mock_upload, \
         patch("app.agent.nodes.output._doc_store", mock_store):

        mock_gen.return_value = b"fake-pdf-bytes"
        mock_upload.return_value = "https://fake.url/blob.pdf"

        result = await output_node(minimal_state)

        assert result["status"] == "completed"
        saved_doc = mock_store.save.call_args[0][0]
        assert saved_doc["tenant_id"] == "poc-tenant"  # default
        assert saved_doc["revision_count"] == 0  # default
