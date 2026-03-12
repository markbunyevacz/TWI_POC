"""Tests for Azure AI Foundry service."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


class TestAIFoundryService:
    """Tests for the AI Foundry LLM service."""

    @pytest.mark.asyncio
    async def test_get_client_initializes_credential(self):
        """Test that client is initialized with proper credentials."""
        with patch("app.services.ai_foundry.ChatCompletionsClient") as MockClient:
            with patch("app.services.ai_foundry.AzureKeyCredential") as MockCred:
                with patch("app.services.ai_foundry.settings") as mock_settings:
                    mock_settings.ai_foundry_endpoint = "https://test.openai.azure.com"
                    mock_settings.ai_foundry_key = "test-key"
                    
                    from app.services.ai_foundry import AIFoundryService
                    # Reset the global client
                    import app.services.ai_foundry as ai_foundry_module
                    ai_foundry_module._client = None
                    
                    service = AIFoundryService()
                    # The client should be created with the endpoint and credential
                    MockClient.assert_called()

    @pytest.mark.asyncio
    async def test_complete_with_valid_prompt(self):
        """Test completion with a valid prompt."""
        with patch("app.services.ai_foundry.ChatCompletionsClient") as MockClient:
            with patch("app.services.ai_foundry.AzureKeyCredential"):
                with patch("app.services.ai_foundry.settings") as mock_settings:
                    mock_settings.ai_foundry_endpoint = "https://test.openai.azure.com"
                    mock_settings.ai_foundry_key = "test-key"
                    mock_settings.ai_model = "gpt-4o"
                    mock_settings.ai_temperature = 0.3
                    mock_settings.ai_max_tokens = 4000
                    
                    # Mock the response
                    mock_response = MagicMock()
                    mock_response.choices = [MagicMock()]
                    mock_response.choices[0].message = MagicMock()
                    mock_response.choices[0].message.content = "Test response"
                    mock_response.usage = MagicMock()
                    mock_response.usage.total_token_count = 100
                    
                    mock_client_instance = MagicMock()
                    mock_client_instance.complete = AsyncMock(return_value=mock_response)
                    MockClient.return_value = mock_client_instance
                    
                    # Reset module state
                    import app.services.ai_foundry as ai_foundry_module
                    ai_foundry_module._client = None
                    
                    from app.services.ai_foundry import AIFoundryService
                    service = AIFoundryService()
                    
                    result = await service.complete("Test prompt")
                    
                    assert result == ("Test response", 100)
                    mock_client_instance.complete.assert_called_once()

    @pytest.mark.asyncio
    async def test_complete_empty_prompt(self):
        """Test completion with empty prompt returns empty response."""
        from app.services.ai_foundry import AIFoundryService
        
        service = AIFoundryService()
        
        # Mock the client
        service._client = MagicMock()
        
        result = await service.complete("")
        
        assert result == ("", 0)

    @pytest.mark.asyncio
    async def test_complete_handles_api_error(self):
        """Test that API errors are handled gracefully."""
        from app.services.ai_foundry import AIFoundryService
        
        service = AIFoundryService()
        
        # Mock the client that raises an exception
        service._client = MagicMock()
        service._client.complete = AsyncMock(side_effect=Exception("API Error"))
        
        result = await service.complete("Test prompt")
        
        # Should return empty response on error
        assert result == ("", 0)


class TestAIFoundryServiceUnit:
    """Unit tests for AIFoundryService with mocking."""

    def test_service_stores_settings(self):
        """Test that service properly stores settings."""
        with patch("app.services.ai_foundry.settings") as mock_settings:
            mock_settings.ai_model = "test-model"
            mock_settings.ai_temperature = 0.5
            mock_settings.ai_max_tokens = 2000
            
            from app.services.ai_foundry import AIFoundryService
            service = AIFoundryService()
            
            assert service.model == "test-model"
            assert service.temperature == 0.5
            assert service.max_tokens == 2000
