"""Tests for the audit_node: event_type derivation, split token fields, and failure safety."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock


def _make_audit_state(**overrides) -> dict:
    base = {
        "user_id": "test-user-001",
        "tenant_id": "poc-tenant",
        "conversation_id": "conv-test-audit",
        "channel": "msteams",
        "message": "Készíts TWI utasítást",
        "intent": "generate_twi",
        "processed_input": None,
        "draft": "some draft",
        "draft_metadata": None,
        "revision_feedback": None,
        "revision_count": 0,
        "status": "completed",
        "pdf_url": None,
        "pdf_blob_name": "twi/conv-test-audit/abc.pdf",
        "llm_model": "gpt-4o",
        "llm_tokens_input": 1250,
        "llm_tokens_output": 2800,
        "approval_timestamp": "2026-03-12T10:00:00Z",
        "messages": [],
    }
    return {**base, **overrides}


class TestAuditEventType:
    @pytest.mark.asyncio
    async def test_completed_status_logs_twi_generated(self):
        mock_store = MagicMock()
        mock_store.log = AsyncMock()

        with patch("app.agent.nodes.audit.AuditStore", return_value=mock_store):
            from app.agent.nodes.audit import audit_node

            await audit_node(_make_audit_state(status="completed"))

        logged = mock_store.log.call_args[0][0]
        assert logged["event_type"] == "twi_generated"

    @pytest.mark.asyncio
    async def test_rejected_status_logs_twi_rejected(self):
        mock_store = MagicMock()
        mock_store.log = AsyncMock()

        with patch("app.agent.nodes.audit.AuditStore", return_value=mock_store):
            from app.agent.nodes.audit import audit_node

            await audit_node(_make_audit_state(status="rejected"))

        logged = mock_store.log.call_args[0][0]
        assert logged["event_type"] == "twi_rejected"

    @pytest.mark.asyncio
    async def test_unknown_status_defaults_to_twi_generated(self):
        mock_store = MagicMock()
        mock_store.log = AsyncMock()

        with patch("app.agent.nodes.audit.AuditStore", return_value=mock_store):
            from app.agent.nodes.audit import audit_node

            await audit_node(_make_audit_state(status="some_unknown"))

        logged = mock_store.log.call_args[0][0]
        assert logged["event_type"] == "twi_generated"


class TestAuditTokenSplit:
    @pytest.mark.asyncio
    async def test_writes_separate_input_output_tokens(self):
        mock_store = MagicMock()
        mock_store.log = AsyncMock()

        with patch("app.agent.nodes.audit.AuditStore", return_value=mock_store):
            from app.agent.nodes.audit import audit_node

            await audit_node(
                _make_audit_state(llm_tokens_input=1250, llm_tokens_output=2800)
            )

        logged = mock_store.log.call_args[0][0]
        assert logged["llm_tokens_input"] == 1250
        assert logged["llm_tokens_output"] == 2800
        assert "llm_tokens_used" not in logged

    @pytest.mark.asyncio
    async def test_none_tokens_written_as_none(self):
        mock_store = MagicMock()
        mock_store.log = AsyncMock()

        with patch("app.agent.nodes.audit.AuditStore", return_value=mock_store):
            from app.agent.nodes.audit import audit_node

            await audit_node(
                _make_audit_state(llm_tokens_input=None, llm_tokens_output=None)
            )

        logged = mock_store.log.call_args[0][0]
        assert logged["llm_tokens_input"] is None
        assert logged["llm_tokens_output"] is None


class TestAuditFailureSafety:
    @pytest.mark.asyncio
    async def test_audit_failure_does_not_raise(self):
        mock_store = MagicMock()
        mock_store.log = AsyncMock(side_effect=Exception("Cosmos DB unavailable"))

        with patch("app.agent.nodes.audit.AuditStore", return_value=mock_store):
            from app.agent.nodes.audit import audit_node

            state = _make_audit_state()
            result = await audit_node(state)

        assert result is state

    @pytest.mark.asyncio
    async def test_audit_node_returns_state_unchanged(self):
        mock_store = MagicMock()
        mock_store.log = AsyncMock()

        with patch("app.agent.nodes.audit.AuditStore", return_value=mock_store):
            from app.agent.nodes.audit import audit_node

            state = _make_audit_state()
            result = await audit_node(state)

        assert result is state


class TestReviseNodeAudit:
    """Verify the inline audit log in revise_node fires a twi_revised event."""

    @pytest.mark.asyncio
    async def test_revision_logs_twi_revised_event(self):
        mock_store = MagicMock()
        mock_store.log = AsyncMock()

        with patch("app.agent.nodes.revise.AuditStore", return_value=mock_store):
            from app.agent.nodes.revise import revise_node

            await revise_node(_make_audit_state(revision_count=1))

        mock_store.log.assert_called_once()
        logged = mock_store.log.call_args[0][0]
        assert logged["event_type"] == "twi_revised"
        assert logged["revision_count"] == 2

    @pytest.mark.asyncio
    async def test_revision_audit_failure_does_not_block(self):
        mock_store = MagicMock()
        mock_store.log = AsyncMock(side_effect=Exception("DB down"))

        with patch("app.agent.nodes.revise.AuditStore", return_value=mock_store):
            from app.agent.nodes.revise import revise_node

            result = await revise_node(_make_audit_state(revision_count=0))

        assert result["revision_count"] == 1
        assert result["status"] == "revision_requested"
