"""Tests for AgentizeBotHandler: card action routing, text message handling, and Telegram fallback."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.bot.bot_handler import AgentizeBotHandler


def _make_turn_context(
    text: str = "",
    value: dict | None = None,
    channel_id: str = "msteams",
    user_id: str = "test-user",
    conversation_id: str = "conv-001",
) -> MagicMock:
    """Build a minimal mock TurnContext."""
    ctx = MagicMock()
    ctx.activity.text = text
    ctx.activity.value = value
    ctx.activity.channel_id = channel_id
    ctx.activity.from_property.id = user_id
    ctx.activity.conversation.id = conversation_id
    ctx.activity.recipient.id = "bot-id"
    ctx.send_activity = AsyncMock()
    return ctx


# ---------------------------------------------------------------------------
# Text message handling
# ---------------------------------------------------------------------------


class TestHandleTextMessage:
    @pytest.mark.asyncio
    async def test_sends_processing_indicator(self):
        with patch.object(AgentizeBotHandler, "__init__", lambda self: None):
            handler = AgentizeBotHandler()
            handler.graph = MagicMock()
            handler.conversation_store = MagicMock()
            handler.conversation_store.get_or_create = AsyncMock()

        ctx = _make_turn_context(text="Készíts TWI utasítást")

        with patch(
            "app.bot.bot_handler.run_agent",
            new=AsyncMock(return_value={"status": "review_needed", "draft": "draft", "draft_metadata": {}}),
        ):
            await handler.on_message_activity(ctx)

        # First call is the processing indicator
        first_call_args = ctx.send_activity.call_args_list[0]
        assert "Feldolgozom" in str(first_call_args)

    @pytest.mark.asyncio
    async def test_review_needed_sends_card(self):
        with patch.object(AgentizeBotHandler, "__init__", lambda self: None):
            handler = AgentizeBotHandler()
            handler.graph = MagicMock()
            handler.conversation_store = MagicMock()
            handler.conversation_store.get_or_create = AsyncMock()

        ctx = _make_turn_context(text="Készíts TWI utasítást")

        with patch(
            "app.bot.bot_handler.run_agent",
            new=AsyncMock(return_value={
                "status": "review_needed",
                "draft": "test draft",
                "draft_metadata": {"model": "test-model"},
            }),
        ):
            await handler.on_message_activity(ctx)

        # Should have sent processing message + card
        assert ctx.send_activity.call_count >= 2

    @pytest.mark.asyncio
    async def test_clarification_needed_sends_text(self):
        with patch.object(AgentizeBotHandler, "__init__", lambda self: None):
            handler = AgentizeBotHandler()
            handler.graph = MagicMock()
            handler.conversation_store = MagicMock()
            handler.conversation_store.get_or_create = AsyncMock()

        ctx = _make_turn_context(text="hello")

        with patch(
            "app.bot.bot_handler.run_agent",
            new=AsyncMock(return_value={"status": "clarification_needed"}),
        ):
            await handler.on_message_activity(ctx)

        # Should include clarification message
        calls = [str(c) for c in ctx.send_activity.call_args_list]
        assert any("pontosítsd" in c for c in calls)

    @pytest.mark.asyncio
    async def test_agent_error_shows_safe_message(self):
        with patch.object(AgentizeBotHandler, "__init__", lambda self: None):
            handler = AgentizeBotHandler()
            handler.graph = MagicMock()
            handler.conversation_store = MagicMock()
            handler.conversation_store.get_or_create = AsyncMock()

        ctx = _make_turn_context(text="test")

        with patch(
            "app.bot.bot_handler.run_agent",
            new=AsyncMock(side_effect=RuntimeError("internal details")),
        ):
            await handler.on_message_activity(ctx)

        # Error message should NOT contain internal exception details
        calls = [str(c) for c in ctx.send_activity.call_args_list]
        assert not any("internal details" in c for c in calls)
        assert any("Hiba" in c for c in calls)


# ---------------------------------------------------------------------------
# Card action routing
# ---------------------------------------------------------------------------


class TestHandleCardAction:
    @pytest.mark.asyncio
    async def test_approve_draft_sends_approval_card(self):
        with patch.object(AgentizeBotHandler, "__init__", lambda self: None):
            handler = AgentizeBotHandler()
            handler.graph = MagicMock()
            handler.conversation_store = MagicMock()
            handler.conversation_store.get_or_create = AsyncMock()

        ctx = _make_turn_context(
            value={"action": "approve_draft", "draft": "test draft", "metadata": {}},
        )

        await handler.on_message_activity(ctx)

        # Should send an approval card (Activity with attachments)
        assert ctx.send_activity.call_count >= 1

    @pytest.mark.asyncio
    async def test_reject_sends_rejection_message(self):
        with patch.object(AgentizeBotHandler, "__init__", lambda self: None):
            handler = AgentizeBotHandler()
            handler.graph = MagicMock()
            handler.conversation_store = MagicMock()
            handler.conversation_store.get_or_create = AsyncMock()

        ctx = _make_turn_context(value={"action": "reject"})

        await handler.on_message_activity(ctx)

        calls = [str(c) for c in ctx.send_activity.call_args_list]
        assert any("Elvettem" in c for c in calls)

    @pytest.mark.asyncio
    async def test_unknown_action_logged(self):
        with patch.object(AgentizeBotHandler, "__init__", lambda self: None):
            handler = AgentizeBotHandler()
            handler.graph = MagicMock()
            handler.conversation_store = MagicMock()
            handler.conversation_store.get_or_create = AsyncMock()

        ctx = _make_turn_context(value={"action": "nonexistent"})

        with patch("app.bot.bot_handler.logger") as mock_logger:
            await handler.on_message_activity(ctx)
            mock_logger.warning.assert_called_once()

    @pytest.mark.asyncio
    async def test_request_edit_resumes_graph(self):
        with patch.object(AgentizeBotHandler, "__init__", lambda self: None):
            handler = AgentizeBotHandler()
            handler.graph = MagicMock()
            handler.conversation_store = MagicMock()
            handler.conversation_store.get_or_create = AsyncMock()

        ctx = _make_turn_context(
            value={
                "action": "request_edit",
                "feedback": "Add temperature check",
                "draft": "old draft",
                "metadata": {},
            },
        )

        with patch(
            "app.bot.bot_handler.run_agent",
            new=AsyncMock(return_value={
                "status": "review_needed",
                "draft": "updated draft",
                "draft_metadata": {},
            }),
        ) as mock_run:
            await handler.on_message_activity(ctx)

            mock_run.assert_called_once()
            call_kwargs = mock_run.call_args
            assert call_kwargs.kwargs.get("resume_from") == "revision"

    @pytest.mark.asyncio
    async def test_final_approve_resumes_graph(self):
        with patch.object(AgentizeBotHandler, "__init__", lambda self: None):
            handler = AgentizeBotHandler()
            handler.graph = MagicMock()
            handler.conversation_store = MagicMock()
            handler.conversation_store.get_or_create = AsyncMock()

        ctx = _make_turn_context(
            value={"action": "final_approve", "draft": "final draft", "metadata": {}},
        )

        with patch(
            "app.bot.bot_handler.run_agent",
            new=AsyncMock(return_value={
                "status": "completed",
                "pdf_url": "https://example.com/test.pdf",
                "title": "Test TWI",
                "draft_metadata": {"model": "test"},
            }),
        ) as mock_run:
            await handler.on_message_activity(ctx)

            mock_run.assert_called_once()
            call_kwargs = mock_run.call_args
            assert call_kwargs.kwargs.get("resume_from") == "output"


# ---------------------------------------------------------------------------
# Telegram fallback
# ---------------------------------------------------------------------------


class TestTelegramFallback:
    def test_is_telegram_returns_true_for_telegram(self):
        assert AgentizeBotHandler._is_telegram("telegram") is True

    def test_is_telegram_returns_false_for_msteams(self):
        assert AgentizeBotHandler._is_telegram("msteams") is False

    @pytest.mark.asyncio
    async def test_send_card_telegram_sends_text(self):
        ctx = MagicMock()
        ctx.send_activity = AsyncMock()

        card = {
            "body": [
                {"type": "TextBlock", "text": "Title"},
                {"type": "TextBlock", "text": "Body text"},
            ],
            "actions": [
                {"type": "Action.OpenUrl", "title": "Download", "url": "https://example.com"},
            ],
        }

        await AgentizeBotHandler._send_card(ctx, card, "telegram")

        ctx.send_activity.assert_called_once()
        sent_text = ctx.send_activity.call_args[0][0]
        assert "Title" in sent_text
        assert "Body text" in sent_text
        assert "https://example.com" in sent_text

    @pytest.mark.asyncio
    async def test_send_card_msteams_sends_adaptive_card(self):
        ctx = MagicMock()
        ctx.send_activity = AsyncMock()

        card = {
            "body": [{"type": "TextBlock", "text": "Test"}],
            "actions": [],
        }

        await AgentizeBotHandler._send_card(ctx, card, "msteams")

        ctx.send_activity.assert_called_once()
        # For msteams, an Activity object is passed (not a plain string)
        sent = ctx.send_activity.call_args[0][0]
        assert hasattr(sent, "type")  # Activity object


# ---------------------------------------------------------------------------
# Welcome card
# ---------------------------------------------------------------------------


class TestOnMembersAdded:
    @pytest.mark.asyncio
    async def test_welcome_card_sent_for_new_member(self):
        with patch.object(AgentizeBotHandler, "__init__", lambda self: None):
            handler = AgentizeBotHandler()
            handler.graph = MagicMock()
            handler.conversation_store = MagicMock()

        ctx = MagicMock()
        ctx.activity.recipient.id = "bot-id"
        ctx.activity.channel_id = "msteams"
        ctx.send_activity = AsyncMock()

        member = MagicMock()
        member.id = "new-user"

        await handler.on_members_added_activity([member], ctx)

        ctx.send_activity.assert_called_once()
