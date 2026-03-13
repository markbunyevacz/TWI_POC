"""Tests for Azure Blob Storage service — upload_pdf() and _get_client()."""

import pytest
from unittest.mock import MagicMock, patch


class TestGetClient:
    """Tests for the singleton blob client factory."""

    def test_client_uses_connection_string(self):
        """_get_client creates a BlobServiceClient from settings.blob_connection."""
        import app.services.blob_storage as mod

        original_client = mod._client
        mod._client = None

        try:
            with (
                patch.object(mod, "BlobServiceClient") as MockBSC,
                patch.object(mod, "settings") as mock_settings,
            ):
                mock_settings.blob_connection = "DefaultEndpointsProtocol=https;AccountName=test;AccountKey=key==;EndpointSuffix=core.windows.net"
                MockBSC.from_connection_string.return_value = MagicMock()

                client = mod._get_client()

                MockBSC.from_connection_string.assert_called_once_with(
                    mock_settings.blob_connection
                )
                assert client is MockBSC.from_connection_string.return_value
        finally:
            mod._client = original_client

    def test_client_is_singleton(self):
        """Repeated calls return the same client instance."""
        import app.services.blob_storage as mod

        original_client = mod._client
        mod._client = None

        try:
            with (
                patch.object(mod, "BlobServiceClient") as MockBSC,
                patch.object(mod, "settings") as mock_settings,
            ):
                mock_settings.blob_connection = "fake-connection"
                MockBSC.from_connection_string.return_value = MagicMock()

                c1 = mod._get_client()
                c2 = mod._get_client()

                assert c1 is c2
                MockBSC.from_connection_string.assert_called_once()
        finally:
            mod._client = original_client


class TestUploadPdf:
    """Tests for the upload_pdf async function."""

    @pytest.mark.asyncio
    async def test_upload_success_returns_sas_url(self):
        """Successful upload returns a URL containing the blob path and a SAS token."""
        mock_blob_client = MagicMock()
        mock_blob_client.upload_blob = MagicMock()
        mock_blob_client.url = (
            "https://testaccount.blob.core.windows.net/container/path/file.pdf"
        )

        mock_container_client = MagicMock()
        mock_container_client.get_blob_client.return_value = mock_blob_client

        mock_service_client = MagicMock()
        mock_service_client.get_container_client.return_value = mock_container_client
        mock_service_client.account_name = "testaccount"
        mock_service_client.credential.account_key = "dGVzdGtleQ=="

        with (
            patch(
                "app.services.blob_storage._get_client",
                return_value=mock_service_client,
            ),
            patch("app.services.blob_storage.settings") as mock_settings,
            patch(
                "app.services.blob_storage.generate_blob_sas", return_value="sig=abc123"
            ),
        ):
            mock_settings.blob_container = "test-container"

            from app.services.blob_storage import upload_pdf

            result = await upload_pdf(b"fake-pdf-bytes", "twi/conv-1/doc.pdf")

        assert "testaccount" in result
        assert "sig=abc123" in result

    @pytest.mark.asyncio
    async def test_upload_calls_blob_client(self):
        """upload_pdf calls upload_blob via asyncio.to_thread."""
        mock_blob_client = MagicMock()
        mock_blob_client.upload_blob = MagicMock()
        mock_blob_client.url = "https://test.blob.core.windows.net/c/f.pdf"

        mock_container_client = MagicMock()
        mock_container_client.get_blob_client.return_value = mock_blob_client

        mock_service_client = MagicMock()
        mock_service_client.get_container_client.return_value = mock_container_client
        mock_service_client.account_name = "test"
        mock_service_client.credential.account_key = "key"

        with (
            patch(
                "app.services.blob_storage._get_client",
                return_value=mock_service_client,
            ),
            patch("app.services.blob_storage.settings") as mock_settings,
            patch("app.services.blob_storage.generate_blob_sas", return_value="sig=x"),
        ):
            mock_settings.blob_container = "c"

            from app.services.blob_storage import upload_pdf

            await upload_pdf(b"bytes", "path.pdf")

        mock_blob_client.upload_blob.assert_called_once()

    @pytest.mark.asyncio
    async def test_upload_handles_missing_account_key(self):
        """When credential has no account_key, falls back to blob URL without SAS."""
        mock_blob_client = MagicMock()
        mock_blob_client.upload_blob = MagicMock()
        mock_blob_client.url = "https://mi.blob.core.windows.net/c/f.pdf"

        mock_container_client = MagicMock()
        mock_container_client.get_blob_client.return_value = mock_blob_client

        mock_service_client = MagicMock()
        mock_service_client.get_container_client.return_value = mock_container_client
        mock_service_client.account_name = "mi"
        mock_service_client.credential = MagicMock(spec=[])

        with (
            patch(
                "app.services.blob_storage._get_client",
                return_value=mock_service_client,
            ),
            patch("app.services.blob_storage.settings") as mock_settings,
        ):
            mock_settings.blob_container = "c"

            from app.services.blob_storage import upload_pdf

            result = await upload_pdf(b"bytes", "path.pdf")

        assert result == mock_blob_client.url

    @pytest.mark.asyncio
    async def test_upload_error_propagates(self):
        """Exceptions from blob upload bubble up to the caller."""
        mock_blob_client = MagicMock()
        mock_blob_client.upload_blob = MagicMock(side_effect=Exception("Upload failed"))

        mock_container_client = MagicMock()
        mock_container_client.get_blob_client.return_value = mock_blob_client

        mock_service_client = MagicMock()
        mock_service_client.get_container_client.return_value = mock_container_client

        with (
            patch(
                "app.services.blob_storage._get_client",
                return_value=mock_service_client,
            ),
            patch("app.services.blob_storage.settings") as mock_settings,
        ):
            mock_settings.blob_container = "c"

            from app.services.blob_storage import upload_pdf

            with pytest.raises(Exception, match="Upload failed"):
                await upload_pdf(b"bytes", "path.pdf")
