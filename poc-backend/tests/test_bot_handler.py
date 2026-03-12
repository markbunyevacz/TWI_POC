"""Tests for bot_handler.py - the main bot activity handler."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone


class TestTelegramHelpers:
    """Test Telegram-specific helper functions."""

    def test_is_telegram_channel(self):
        """Test Telegram channel detection."""
        from app.bot.bot_handler import _is_telegram_channel
        
        assert _is_telegram_channel("telegram") is True
        assert _is_telegram_channel("Telegram") is True
        assert _is_telegram_channel("TELEGRAM") is True
        assert _is_telegram_channel("msteams") is False
        assert _is_telegram_channel("") is False
        assert _is_telegram_channel(None) is False

    def test_format_telegram_review(self):
        """Test Telegram review message formatting."""
        from app.bot.bot_handler import _format_telegram_review
        
        draft = "## CNC-01 beállítása\n\n1. Kapcsold be"
        metadata = {
            "title": "CNC-01 gép beállítása",
            "model": "mistral-large",
            "generated_at": "2026-03-06"
        }
        
        result = _format_telegram_review(draft, metadata)
        
        assert "📋 *CNC-01 gép beállítása*" in result
        assert "mistral-large" in result
        assert "2026-03-06" in result
        assert "CNC-01 beállítása" in result
        assert "Elfogadás" in result
        assert "Módosítás" in result
        assert "Elutasítás" in result

    def test_format_telegram_approval(self):
        """Test Telegram approval message formatting."""
        from app.bot.bot_handler import _format_telegram_approval
        
        metadata = {"title": "Végleges dokumentum"}
        
        result = _format_telegram_approval("draft content", metadata)
        
        assert "📄 *Végleges dokumentum*" in result
        assert "Igen" in result
        assert "Nem" in result

    def test_format_telegram_result(self):
        """Test Telegram result message formatting."""
        from app.bot.bot_handler import _format_telegram_result
        
        metadata = {"approved_by": "user-123"}
        
        result = _format_telegram_result(
            "https://example.com/file.pdf",
            "CNC-01 beállítás",
            metadata
        )
        
        assert "✅ *Dokumentum elkészült!*" in result
        assert "CNC-01 beállítás" in result
        assert "user-123" in result
        assert "https://example.com/file.pdf" in result


class TestBotHandler:
    """Test the AgentizeBotHandler class."""

    @pytest.fixture
    def mock_turn_context(self):
        """Create a mock TurnContext."""
        mock = MagicMock()
        mock.activity = MagicMock()
        mock.activity.from_property = MagicMock()
        mock.activity.from_property.id = "user-123"
        mock.activity.conversation = MagicMock()
        mock.activity.conversation.id = "conv-456"
        mock.activity.channel_id = "msteams"
        mock.activity.text = "Hello"
        mock.activity.value = None
        mock.send_activity = AsyncMock()
        return mock

    @pytest.fixture
    def mock_telegram_context(self, mock_turn_context):
        """Create a mock TurnContext for Telegram."""
        mock_turn_context.activity.channel_id = "telegram"
        mock_turn_context.activity.text = "Készíts TWI utasítást"
        return mock_turn_context

    @pytest.mark.asyncio
    async def test_on_message_activity_calls_get_or_create(self, mock_turn_context):
        """Test that message activity tracks conversation in Cosmos DB."""
        with patch("app.bot.bot_handler.ConversationStore") as MockStore:
            mock_store = MagicMock()
            mock_store.get_or_create = AsyncMock()
            MockStore.return_value = mock_store
            
            from app.bot.bot_handler import AgentizeBotHandler
            handler = AgentizeBotHandler()
            
            with patch.object(handler, "_get_graph", new_callable=AsyncMock) as mock_get_graph:
                mock_get_graph.return_value = MagicMock()
                with patch("app.bot.bot_handler.run_agent", new_callable=AsyncMock) as mock_run:
                    mock_run.return_value = {"status": "clarification_needed"}
                    await handler.on_message_activity(mock_turn_context)
            
            mock_store.get_or_create.assert_called_once()

    @pytest.mark.asyncio
    async def test_on_members_added_sends_welcome_card(self):
        """Test that bot sends welcome card when added to conversation."""
        from app.bot.bot_handler import AgentizeBotHandler

        handler = AgentizeBotHandler()

        members_added = [MagicMock()]
        members_added[0].id = "new-user"

        turn_context = MagicMock()
        turn_context.activity = MagicMock()
        turn_context.activity.recipient = MagicMock()
        turn_context.activity.recipient.id = "bot-id"
        turn_context.send_activity = AsyncMock()

        with patch.object(handler, "_send_card", new_callable=AsyncMock) as mock_send:
            await handler.on_members_added_activity(members_added, turn_context)
            mock_send.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_text_message_telegram_routes_correctly(self, mock_telegram_context):
        """Test that Telegram messages are routed to Telegram handler."""
        from app.bot.bot_handler import AgentizeBotHandler

        handler = AgentizeBotHandler()
        handler._get_graph = AsyncMock(return_value=MagicMock())
        handler._handle_telegram_response = AsyncMock()

        with patch("app.bot.bot_handler.run_agent", new_callable=AsyncMock) as mock_run:
            mock_run.return_value = {"status": "review_needed", "draft": "test", "draft_metadata": {}}
            await handler._handle_text_message(
                mock_telegram_context,
                "test message",
                "conv-123",
                "user-456",
                "telegram"
            )

        handler._handle_telegram_response.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_telegram_text_approve(self):
        """Test handling 'Igen' approval response from Telegram."""
        from app.bot.bot_handler import AgentizeBotHandler
        
        handler = AgentizeBotHandler()
        handler._get_graph = AsyncMock(return_value=MagicMock())
        
        turn_context = MagicMock()
        turn_context.send_activity = AsyncMock()
        
        with patch("app.bot.bot_handler.run_agent", new_callable=AsyncMock) as mock_run:
            mock_run.return_value = {
                "draft": "content",
                "draft_metadata": {},
                "pdf_url": "https://example.com/pdf",
                "title": "Test Doc"
            }
            
            await handler._handle_telegram_text(
                turn_context,
                "igen",
                "conv-123",
                "user-456"
            )
            
            assert turn_context.send_activity.call_count >= 1

    @pytest.mark.asyncio
    async def test_handle_telegram_text_reject(self):
        """Test handling 'Nem' rejection response from Telegram."""
        from app.bot.bot_handler import AgentizeBotHandler
        
        handler = AgentizeBotHandler()
        
        turn_context = MagicMock()
        turn_context.send_activity = AsyncMock()
        
        await handler._handle_telegram_text(
            turn_context,
            "nem",
            "conv-123",
            "user-456"
        )
        
        call_args = [str(c) for c in turn_context.send_activity.call_args_list]
        assert any("Elvettem" in str(c) or "törlés" in str(c) for c in call_args)

    @pytest.mark.asyncio
    async def test_handle_telegram_text_unknown_command(self):
        """Test handling unknown command from Telegram."""
        from app.bot.bot_handler import AgentizeBotHandler
        
        handler = AgentizeBotHandler()
        
        turn_context = MagicMock()
        turn_context.send_activity = AsyncMock()
        
        await handler._handle_telegram_text(
            turn_context,
            "random text",
            "conv-123",
            "user-456"
        )
        
        call_args = [str(c) for c in turn_context.send_activity.call_args_list]
        assert any("parancsokat" in str(c) or "help" in str(c).lower() for c in call_args)

    @pytest.mark.asyncio
    async def test_handle_card_action_approve_draft_telegram(self):
        """Test approve_draft action handling for Telegram."""
        from app.bot.bot_handler import AgentizeBotHandler
        
        handler = AgentizeBotHandler()
        handler._get_graph = AsyncMock(return_value=MagicMock())
        
        turn_context = MagicMock()
        turn_context.activity.channel_id = "telegram"
        turn_context.send_activity = AsyncMock()
        
        value = {
            "action": "approve_draft",
            "draft": "test draft",
            "metadata": {"title": "Test"}
        }
        
        with patch("app.bot.bot_handler.run_agent", new_callable=AsyncMock) as mock_run:
            mock_run.return_value = {
                "draft": "content",
                "draft_metadata": {},
                "pdf_url": "https://example.com/pdf",
                "title": "Test Doc"
            }
            
            await handler._handle_card_action(
                turn_context,
                value,
                "conv-123",
                "user-456"
            )
        
        turn_context.send_activity.assert_called()

    @pytest.mark.asyncio
    async def test_handle_card_action_reject(self):
        """Test reject action handling."""
        from app.bot.bot_handler import AgentizeBotHandler
        
        handler = AgentizeBotHandler()
        
        turn_context = MagicMock()
        turn_context.send_activity = AsyncMock()
        
        value = {"action": "reject"}
        
        await handler._handle_card_action(
            turn_context,
            value,
            "conv-123",
            "user-456"
        )
        
        call_args = [str(c) for c in turn_context.send_activity.call_args_list]
        assert any("Elvettem" in str(c) for c in call_args)


class TestRequestEditSource:
    """Verify that request_edit from the approval card passes as_node='review'."""

    @pytest.mark.asyncio
    async def test_request_edit_from_approval_card_passes_as_node_review(self):
        """Back-to-editing from approval card must route via after_review."""
        from app.bot.bot_handler import AgentizeBotHandler

        handler = AgentizeBotHandler()
        handler._get_graph = AsyncMock(return_value=MagicMock())

        turn_context = MagicMock()
        turn_context.activity.channel_id = "msteams"
        turn_context.send_activity = AsyncMock()

        value = {
            "action": "request_edit",
            "source": "approval",
            "draft": "test draft",
            "metadata": {},
            "feedback": "fix step 3",
        }

        with patch("app.bot.bot_handler.run_agent", new_callable=AsyncMock) as mock_run:
            mock_run.return_value = {
                "status": "review_needed",
                "draft": "revised draft",
                "draft_metadata": {"model": "gpt-4o", "generated_at": "now"},
            }
            await handler._handle_card_action(
                turn_context, value, "conv-123", "user-456"
            )

            mock_run.assert_called_once()
            _, kwargs = mock_run.call_args
            assert kwargs["as_node"] == "review"

    @pytest.mark.asyncio
    async def test_request_edit_from_review_card_passes_as_node_none(self):
        """Edit from the review card should NOT override as_node."""
        from app.bot.bot_handler import AgentizeBotHandler

        handler = AgentizeBotHandler()
        handler._get_graph = AsyncMock(return_value=MagicMock())

        turn_context = MagicMock()
        turn_context.activity.channel_id = "msteams"
        turn_context.send_activity = AsyncMock()

        value = {
            "action": "request_edit",
            "draft": "test draft",
            "metadata": {},
            "feedback": "minor fix",
        }

        with patch("app.bot.bot_handler.run_agent", new_callable=AsyncMock) as mock_run:
            mock_run.return_value = {
                "status": "review_needed",
                "draft": "revised draft",
                "draft_metadata": {"model": "gpt-4o", "generated_at": "now"},
            }
            await handler._handle_card_action(
                turn_context, value, "conv-123", "user-456"
            )

            mock_run.assert_called_once()
            _, kwargs = mock_run.call_args
            assert kwargs["as_node"] is None


class TestBotHandlerEdgeCases:
    """Test edge cases and error handling."""

    @pytest.mark.asyncio
    async def test_run_agent_exception_handling(self):
        """Test that exceptions in run_agent are caught and handled."""
        from app.bot.bot_handler import AgentizeBotHandler
        
        handler = AgentizeBotHandler()
        handler._get_graph = AsyncMock(return_value=MagicMock())
        
        turn_context = MagicMock()
        turn_context.send_activity = AsyncMock()
        
        with patch("app.bot.bot_handler.run_agent", new_callable=AsyncMock) as mock_run:
            mock_run.side_effect = Exception("Test error")
            
            await handler._handle_text_message(
                turn_context,
                "test",
                "conv-123",
                "user-456",
                "msteams"
            )
        
        call_args = [str(c) for c in turn_context.send_activity.call_args_list]
        assert any("Hiba" in str(c) for c in call_args)
