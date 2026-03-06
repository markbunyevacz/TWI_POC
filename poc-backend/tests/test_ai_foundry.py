"""Tests for the Azure AI Foundry service client (call_llm)."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


class TestCallLlm:
    @pytest.mark.asyncio
    async def test_returns_content_and_token_count(self):
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "generate_twi"
        mock_response.usage.prompt_tokens = 10
        mock_response.usage.completion_tokens = 5
        mock_response.usage.total_tokens = 15

        mock_client = AsyncMock()
        mock_client.complete = AsyncMock(return_value=mock_response)

        with patch("app.services.ai_foundry._get_client", return_value=mock_client):
            from app.services.ai_foundry import call_llm

            content, tokens = await call_llm(prompt="test prompt")

        assert content == "generate_twi"
        assert tokens == 15

    @pytest.mark.asyncio
    async def test_system_prompt_included_when_provided(self):
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "response"
        mock_response.usage.prompt_tokens = 10
        mock_response.usage.completion_tokens = 5
        mock_response.usage.total_tokens = 15

        mock_client = AsyncMock()
        mock_client.complete = AsyncMock(return_value=mock_response)

        with patch("app.services.ai_foundry._get_client", return_value=mock_client):
            from app.services.ai_foundry import call_llm

            await call_llm(prompt="test", system_prompt="You are a classifier")

        call_args = mock_client.complete.call_args
        messages = call_args.kwargs["messages"]
        assert messages[0]["role"] == "system"
        assert messages[0]["content"] == "You are a classifier"
        assert messages[1]["role"] == "user"

    @pytest.mark.asyncio
    async def test_no_system_prompt_sends_only_user_message(self):
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "response"
        mock_response.usage.prompt_tokens = 10
        mock_response.usage.completion_tokens = 5
        mock_response.usage.total_tokens = 15

        mock_client = AsyncMock()
        mock_client.complete = AsyncMock(return_value=mock_response)

        with patch("app.services.ai_foundry._get_client", return_value=mock_client):
            from app.services.ai_foundry import call_llm

            await call_llm(prompt="test")

        call_args = mock_client.complete.call_args
        messages = call_args.kwargs["messages"]
        assert len(messages) == 1
        assert messages[0]["role"] == "user"

    @pytest.mark.asyncio
    async def test_custom_temperature_and_max_tokens_passed(self):
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "response"
        mock_response.usage.prompt_tokens = 10
        mock_response.usage.completion_tokens = 5
        mock_response.usage.total_tokens = 15

        mock_client = AsyncMock()
        mock_client.complete = AsyncMock(return_value=mock_response)

        with patch("app.services.ai_foundry._get_client", return_value=mock_client):
            from app.services.ai_foundry import call_llm

            await call_llm(prompt="test", temperature=0.1, max_tokens=20)

        call_args = mock_client.complete.call_args
        assert call_args.kwargs["temperature"] == 0.1
        assert call_args.kwargs["max_tokens"] == 20
