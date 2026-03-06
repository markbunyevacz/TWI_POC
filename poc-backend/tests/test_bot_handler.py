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


def _make_handler_with_no_paused_state():
    """Create a handler whose graph.aget_state returns no paused state."""
    with patch.object(AgentizeBotHandler, "__init__", lambda self: None):
        handler = AgentizeBotHandler()
        handler.graph = MagicMock()
        # aget_state returns a snapshot with no pending interrupts
        mock_state = MagicMock()
        mock_state.next = ()  # empty = no paused interrupt
        handler.graph.aget_state = AsyncMock(return_value=mock_state)
        handler.conversation_store = MagicMock()
        handler.conversation_store.get_or_create = AsyncMock()
    return handler


class TestHandleTextMessage:
    @pytest.mark.asyncio
    async def test_sends_processing_indicator(self):
        handler = _make_handler_with_no_paused_state()

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
        handler = _make_handler_with_no_paused_state()

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
        handler = _make_handler_with_no_paused_state()

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
        handler = _make_handler_with_no_paused_state()

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

    @pytest.mark.asyncio
    async def test_unexpected_exception_shows_safe_message(self):
        """Blanket Exception catch returns a generic Hungarian error message."""
        handler = _make_handler_with_no_paused_state()

        ctx = _make_turn_context(text="test")

        with patch(
            "app.bot.bot_handler.run_agent",
            new=AsyncMock(side_effect=Exception("segfault-like crash")),
        ):
            await handler.on_message_activity(ctx)

        calls = [str(c) for c in ctx.send_activity.call_args_list]
        assert not any("segfault" in c for c in calls)
        assert any("Váratlan hiba" in c for c in calls)

    @pytest.mark.asyncio
    async def test_error_status_shows_error_message(self):
        """When run_agent returns status='error', user gets an error message."""
        handler = _make_handler_with_no_paused_state()

        ctx = _make_turn_context(text="test")

        with patch(
            "app.bot.bot_handler.run_agent",
            new=AsyncMock(return_value={"status": "error"}),
        ):
            await handler.on_message_activity(ctx)

        calls = [str(c) for c in ctx.send_activity.call_args_list]
        assert any("Hiba" in c for c in calls)

    @pytest.mark.asyncio
    async def test_concurrent_message_on_paused_graph_warns_user(self):
        """If graph is paused at an interrupt, a new text message warns the user."""
        with patch.object(AgentizeBotHandler, "__init__", lambda self: None):
            handler = AgentizeBotHandler()
            handler.graph = MagicMock()
            # Simulate a paused graph (next is non-empty)
            mock_state = MagicMock()
            mock_state.next = ("review",)
            handler.graph.aget_state = AsyncMock(return_value=mock_state)
            handler.conversation_store = MagicMock()
            handler.conversation_store.get_or_create = AsyncMock()

        ctx = _make_turn_context(text="new message")

        with patch("app.bot.bot_handler.run_agent", new=AsyncMock()) as mock_run:
            await handler.on_message_activity(ctx)
            # run_agent should NOT be called — user should be warned instead
            mock_run.assert_not_called()

        calls = [str(c) for c in ctx.send_activity.call_args_list]
        assert any("folyamatban" in c for c in calls)


# ---------------------------------------------------------------------------
# Card action routing
# ---------------------------------------------------------------------------


def _make_handler_for_card_action():
    """Create a handler for card action tests (no aget_state needed)."""
    with patch.object(AgentizeBotHandler, "__init__", lambda self: None):
        handler = AgentizeBotHandler()
        handler.graph = MagicMock()
        handler.conversation_store = MagicMock()
        handler.conversation_store.get_or_create = AsyncMock()
    return handler


class TestHandleCardAction:
    @pytest.mark.asyncio
    async def test_approve_draft_sends_approval_card(self):
        handler = _make_handler_for_card_action()

        ctx = _make_turn_context(
            value={"action": "approve_draft", "draft": "test draft", "metadata": {}},
        )

        await handler.on_message_activity(ctx)

        # Should send an approval card (Activity with attachments)
        assert ctx.send_activity.call_count >= 1

    @pytest.mark.asyncio
    async def test_reject_sends_rejection_message(self):
        handler = _make_handler_for_card_action()

        ctx = _make_turn_context(value={"action": "reject"})

        await handler.on_message_activity(ctx)

        calls = [str(c) for c in ctx.send_activity.call_args_list]
        assert any("Elvettem" in c for c in calls)

    @pytest.mark.asyncio
    async def test_unknown_action_logged(self):
        handler = _make_handler_for_card_action()

        ctx = _make_turn_context(value={"action": "nonexistent"})

        with patch("app.bot.bot_handler.logger") as mock_logger:
            await handler.on_message_activity(ctx)
            mock_logger.warning.assert_called_once()

    @pytest.mark.asyncio
    async def test_request_edit_resumes_graph(self):
        handler = _make_handler_for_card_action()

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
        handler = _make_handler_for_card_action()

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

    @pytest.mark.asyncio
    async def test_request_edit_error_shows_safe_message(self):
        """When run_agent raises during request_edit, user gets safe error."""
        handler = _make_handler_for_card_action()

        ctx = _make_turn_context(
            value={"action": "request_edit", "feedback": "fix it"},
        )

        with patch(
            "app.bot.bot_handler.run_agent",
            new=AsyncMock(side_effect=RuntimeError("LLM timeout")),
        ):
            await handler.on_message_activity(ctx)

        calls = [str(c) for c in ctx.send_activity.call_args_list]
        assert not any("LLM timeout" in c for c in calls)
        assert any("Hiba" in c for c in calls)

    @pytest.mark.asyncio
    async def test_request_edit_unexpected_error_shows_safe_message(self):
        """Blanket Exception during request_edit returns generic error."""
        handler = _make_handler_for_card_action()

        ctx = _make_turn_context(
            value={"action": "request_edit", "feedback": "fix it"},
        )

        with patch(
            "app.bot.bot_handler.run_agent",
            new=AsyncMock(side_effect=Exception("unknown crash")),
        ):
            await handler.on_message_activity(ctx)

        calls = [str(c) for c in ctx.send_activity.call_args_list]
        assert not any("unknown crash" in c for c in calls)
        assert any("Váratlan hiba" in c for c in calls)

    @pytest.mark.asyncio
    async def test_final_approve_error_shows_safe_message(self):
        """When run_agent raises during final_approve, user gets safe error."""
        handler = _make_handler_for_card_action()

        ctx = _make_turn_context(
            value={"action": "final_approve", "draft": "d", "metadata": {}},
        )

        with patch(
            "app.bot.bot_handler.run_agent",
            new=AsyncMock(side_effect=RuntimeError("PDF gen failed")),
        ):
            await handler.on_message_activity(ctx)

        calls = [str(c) for c in ctx.send_activity.call_args_list]
        assert not any("PDF gen failed" in c for c in calls)
        assert any("PDF generálás sikertelen" in c or "Hiba" in c for c in calls)

    @pytest.mark.asyncio
    async def test_final_approve_unexpected_error_shows_safe_message(self):
        """Blanket Exception during final_approve returns generic error."""
        handler = _make_handler_for_card_action()

        ctx = _make_turn_context(
            value={"action": "final_approve", "draft": "d", "metadata": {}},
        )

        with patch(
            "app.bot.bot_handler.run_agent",
            new=AsyncMock(side_effect=Exception("kaboom")),
        ):
            await handler.on_message_activity(ctx)

        calls = [str(c) for c in ctx.send_activity.call_args_list]
        assert not any("kaboom" in c for c in calls)
        assert any("Váratlan hiba" in c for c in calls)


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
