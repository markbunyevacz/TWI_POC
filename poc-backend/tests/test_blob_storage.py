"""Tests for Azure Blob Storage service."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


class TestBlobStorageService:
    """Tests for the Blob Storage service."""

    @pytest.mark.asyncio
    async def test_upload_pdf_success(self):
        """Test successful PDF upload."""
        with patch("app.services.blob_storage.BlobServiceClient") as MockClient:
            with patch("app.services.blob_storage.settings") as mock_settings:
                mock_settings.blob_connection = "DefaultEndpointsProtocol=https;AccountName=test;AccountKey=testkey==;EndpointSuffix=core.windows.net"
                mock_settings.blob_container = "test-container"
                
                # Mock the blob client
                mock_blob_client = MagicMock()
                mock_blob_client.upload_blob = AsyncMock()
                
                mock_container_client = MagicMock()
                mock_container_client.get_blob_client = MagicMock(return_value=mock_blob_client)
                
                mock_client_instance = MagicMock()
                mock_client_instance.get_container_client = MagicMock(return_value=mock_container_client)
                MockClient.from_connection_string.return_value = mock_client_instance
                
                # Reset module state
                import app.services.blob_storage as blob_module
                blob_module._client = None
                
                from app.services.blob_storage import upload_pdf
                
                result = await upload_pdf(b"fake pdf bytes", "test/path/file.pdf")
                
                assert "test-container" in result
                assert "test" in result
                assert "path" in result

    @pytest.mark.asyncio
    async def test_upload_pdf_handles_error(self):
        """Test that upload errors are handled gracefully."""
        with patch("app.services.blob_storage.BlobServiceClient") as MockClient:
            with patch("app.services.blob_storage.settings") as mock_settings:
                mock_settings.blob_connection = "fake-connection-string"
                mock_settings.blob_container = "test-container"
                
                mock_client_instance = MagicMock()
                mock_client_instance.get_container_client = MagicMock(side_effect=Exception("Upload failed"))
                MockClient.from_connection_string.return_value = mock_client_instance
                
                # Reset module state
                import app.services.blob_storage as blob_module
                blob_module._client = None
                
                from app.services.blob_storage import upload_pdf
                
                result = await upload_pdf(b"fake pdf bytes", "test/file.pdf")
                
                # Should return empty string on error
                assert result == ""

    @pytest.mark.asyncio
    async def test_get_blob_url_generates_correct_url(self):
        """Test that blob URL is generated correctly."""
        with patch("app.services.blob_storage.settings") as mock_settings:
            mock_settings.blob_connection = "DefaultEndpointsProtocol=https;AccountName=testaccount;AccountKey==;EndpointSuffix=core.windows.net"
            
            from app.services.blob_storage import BlobStorageService
            
            service = BlobStorageService()
            url = service._get_blob_url("path/to/file.pdf")
            
            assert "testaccount" in url
            assert "path/to/file.pdf" in url
            assert ".pdf" in url


class TestBlobStorageServiceUnit:
    """Unit tests for BlobStorageService."""

    def test_service_stores_container_name(self):
        """Test that service stores container name from settings."""
        with patch("app.services.blob_storage.settings") as mock_settings:
            mock_settings.blob_container = "my-container"
            
            from app.services.blob_storage import BlobStorageService
            service = BlobStorageService()
            
            assert service.container_name == "my-container"

    def test_client_is_singleton(self):
        """Test that the blob client is a singleton."""
        with patch("app.services.blob_storage.BlobServiceClient") as MockClient:
            with patch("app.services.blob_storage.settings") as mock_settings:
                mock_settings.blob_connection = "test-connection"
                mock_settings.blob_container = "test-container"
                
                MockClient.from_connection_string.return_value = MagicMock()
                
                # Reset module state
                import app.services.blob_storage as blob_module
                blob_module._client = None
                
                from app.services.blob_storage import BlobStorageService
                
                service1 = BlobStorageService()
                client1 = service1._client
                
                service2 = BlobStorageService()
                client2 = service2._client
                
                # Should be the same client instance (singleton)
                assert client1 is client2
