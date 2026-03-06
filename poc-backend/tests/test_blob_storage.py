"""Tests for the Azure Blob Storage service client (upload_pdf)."""

import pytest
from unittest.mock import MagicMock, patch, AsyncMock


class TestUploadPdf:
    @pytest.mark.asyncio
    async def test_upload_returns_sas_url(self):
        mock_blob_client = MagicMock()
        mock_blob_client.upload_blob = MagicMock()
        mock_blob_client.url = "https://storage.blob.core.windows.net/pdf-output/test.pdf"

        mock_container_client = MagicMock()
        mock_container_client.get_blob_client.return_value = mock_blob_client

        mock_client = MagicMock()
        mock_client.get_container_client.return_value = mock_container_client
        mock_client.account_name = "teststorage"
        mock_client.credential.account_key = "fake-key"

        with patch("app.services.blob_storage._get_client", return_value=mock_client), \
             patch("app.services.blob_storage.generate_blob_sas", return_value="sas-token"), \
             patch("asyncio.to_thread", new_callable=AsyncMock):
            from app.services.blob_storage import upload_pdf

            result = await upload_pdf(b"fake-pdf", "twi/conv-1/test.pdf")

        assert "sas-token" in result
        assert "storage.blob.core.windows.net" in result

    @pytest.mark.asyncio
    async def test_upload_raises_on_missing_account_key(self):
        mock_blob_client = MagicMock()
        mock_blob_client.upload_blob = MagicMock()
        mock_blob_client.url = "https://storage.blob.core.windows.net/pdf-output/test.pdf"

        mock_container_client = MagicMock()
        mock_container_client.get_blob_client.return_value = mock_blob_client

        mock_client = MagicMock()
        mock_client.get_container_client.return_value = mock_container_client
        mock_client.account_name = "teststorage"
        # Simulate credential without account_key attribute
        mock_client.credential = MagicMock(spec=[])

        with patch("app.services.blob_storage._get_client", return_value=mock_client), \
             patch("asyncio.to_thread", new_callable=AsyncMock):
            from app.services.blob_storage import upload_pdf

            with pytest.raises(RuntimeError, match="account_key"):
                await upload_pdf(b"fake-pdf", "twi/conv-1/test.pdf")
