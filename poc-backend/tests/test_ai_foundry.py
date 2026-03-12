"""Tests for Azure AI Foundry service — call_llm() and _get_client()."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


class TestGetClient:
    """Tests for the singleton client factory."""

    def test_get_client_initializes_with_credentials(self):
        """Client is constructed with endpoint + AzureKeyCredential from settings."""
        import app.services.ai_foundry as mod
        original_client = mod._client
        mod._client = None

        try:
            with patch.object(mod, "AsyncChatCompletionsClient") as MockClient, \
                 patch.object(mod, "AzureKeyCredential") as MockCred, \
                 patch.object(mod, "settings") as mock_settings:
                mock_settings.ai_foundry_endpoint = "https://test.openai.azure.com"
                mock_settings.ai_foundry_key = "test-key"

                mod._get_client()

                MockCred.assert_called_once_with("test-key")
                MockClient.assert_called_once_with(
                    endpoint="https://test.openai.azure.com",
                    credential=MockCred.return_value,
                )
        finally:
            mod._client = original_client

    def test_client_is_singleton(self):
        """Repeated calls return the same client instance."""
        import app.services.ai_foundry as mod
        original_client = mod._client
        mod._client = None

        try:
            with patch.object(mod, "AsyncChatCompletionsClient") as MockClient, \
                 patch.object(mod, "AzureKeyCredential"), \
                 patch.object(mod, "settings") as mock_settings:
                mock_settings.ai_foundry_endpoint = "https://test.openai.azure.com"
                mock_settings.ai_foundry_key = "test-key"
                MockClient.return_value = MagicMock()

                c1 = mod._get_client()
                c2 = mod._get_client()

                assert c1 is c2
                MockClient.assert_called_once()
        finally:
            mod._client = original_client


class TestCallLlm:
    """Tests for the call_llm async function."""

    @pytest.mark.asyncio
    async def test_returns_content_and_tokens(self):
        """Successful call returns (content_str, total_tokens)."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Generated TWI content"
        mock_response.usage.total_tokens = 150
        mock_response.usage.prompt_tokens = 50
        mock_response.usage.completion_tokens = 100

        mock_client = MagicMock()
        mock_client.complete = AsyncMock(return_value=mock_response)

        with patch("app.services.ai_foundry._get_client", return_value=mock_client), \
             patch("app.services.ai_foundry.settings") as mock_settings:
            mock_settings.ai_model = "gpt-4o"
            mock_settings.ai_temperature = 0.3
            mock_settings.ai_max_tokens = 4000

            from app.services.ai_foundry import call_llm
            result = await call_llm("Test prompt")

        assert result == ("Generated TWI content", 150)
        mock_client.complete.assert_called_once()

    @pytest.mark.asyncio
    async def test_system_prompt_prepended_to_messages(self):
        """When system_prompt is provided, messages list starts with system role."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "response"
        mock_response.usage.total_tokens = 10
        mock_response.usage.prompt_tokens = 5
        mock_response.usage.completion_tokens = 5

        mock_client = MagicMock()
        mock_client.complete = AsyncMock(return_value=mock_response)

        with patch("app.services.ai_foundry._get_client", return_value=mock_client), \
             patch("app.services.ai_foundry.settings") as mock_settings:
            mock_settings.ai_model = "gpt-4o"
            mock_settings.ai_temperature = 0.3
            mock_settings.ai_max_tokens = 4000

            from app.services.ai_foundry import call_llm
            await call_llm("user prompt", system_prompt="system instruction")

        call_args = mock_client.complete.call_args
        messages = call_args.kwargs["messages"]
        assert messages[0] == {"role": "system", "content": "system instruction"}
        assert messages[1] == {"role": "user", "content": "user prompt"}

    @pytest.mark.asyncio
    async def test_custom_temperature_and_max_tokens(self):
        """Explicit temperature/max_tokens override settings defaults."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "response"
        mock_response.usage.total_tokens = 10
        mock_response.usage.prompt_tokens = 5
        mock_response.usage.completion_tokens = 5

        mock_client = MagicMock()
        mock_client.complete = AsyncMock(return_value=mock_response)

        with patch("app.services.ai_foundry._get_client", return_value=mock_client), \
             patch("app.services.ai_foundry.settings") as mock_settings:
            mock_settings.ai_model = "gpt-4o"
            mock_settings.ai_temperature = 0.3
            mock_settings.ai_max_tokens = 4000

            from app.services.ai_foundry import call_llm
            await call_llm("prompt", temperature=0.1, max_tokens=20)

        call_args = mock_client.complete.call_args
        assert call_args.kwargs["temperature"] == 0.1
        assert call_args.kwargs["max_tokens"] == 20

    @pytest.mark.asyncio
    async def test_api_error_propagates(self):
        """Exceptions from the Azure client bubble up to the caller."""
        mock_client = MagicMock()
        mock_client.complete = AsyncMock(side_effect=Exception("API Error"))

        with patch("app.services.ai_foundry._get_client", return_value=mock_client), \
             patch("app.services.ai_foundry.settings") as mock_settings:
            mock_settings.ai_model = "gpt-4o"
            mock_settings.ai_temperature = 0.3
            mock_settings.ai_max_tokens = 4000

            from app.services.ai_foundry import call_llm

            with pytest.raises(Exception, match="API Error"):
                await call_llm("Test prompt")
