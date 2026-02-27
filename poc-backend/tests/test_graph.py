"""Tests for the LangGraph agent graph: routing, revision loop, and state transitions."""

import pytest
from unittest.mock import AsyncMock, patch

from app.agent.graph import (
    should_generate,
    after_review,
    after_revision,
    create_agent_graph,
    _build_resume_state,
)
from langgraph.graph import END


# ---------------------------------------------------------------------------
# Shared state fixture helper
# ---------------------------------------------------------------------------

def _make_state(**overrides) -> dict:
    base = {
        "user_id": "test-user",
        "tenant_id": "poc-tenant",
        "conversation_id": "conv-001",
        "channel": "msteams",
        "message": "Készíts TWI utasítást",
        "intent": None,
        "processed_input": None,
        "draft": None,
        "draft_metadata": None,
        "revision_feedback": None,
        "revision_count": 0,
        "status": "processing",
        "pdf_url": None,
        "pdf_blob_name": None,
        "llm_model": None,
        "llm_tokens_used": None,
        "approval_timestamp": None,
        "messages": [],
    }
    return {**base, **overrides}


# ---------------------------------------------------------------------------
# Routing edge functions
# ---------------------------------------------------------------------------


class TestShouldGenerate:
    def test_generate_twi_routes_to_process_input(self):
        assert should_generate({"intent": "generate_twi"}) == "process_input"

    def test_edit_twi_routes_to_process_input(self):
        assert should_generate({"intent": "edit_twi"}) == "process_input"

    def test_question_routes_to_generate(self):
        assert should_generate({"intent": "question"}) == "generate"

    def test_unknown_routes_to_clarify(self):
        assert should_generate({"intent": "unknown"}) == "clarify"

    def test_missing_intent_defaults_to_clarify(self):
        assert should_generate({}) == "clarify"


class TestAfterReview:
    def test_approved_routes_to_approve(self):
        assert after_review({"status": "approved"}) == "approve"

    def test_revision_requested_routes_to_revise(self):
        assert after_review({"status": "revision_requested"}) == "revise"

    def test_rejected_routes_to_end(self):
        assert after_review({"status": "rejected"}) == END

    def test_unknown_status_routes_to_end(self):
        assert after_review({"status": "something_else"}) == END


class TestAfterRevision:
    def test_below_max_routes_to_review(self):
        assert after_revision({"revision_count": 1}) == "review"

    def test_at_max_routes_to_approve(self):
        assert after_revision({"revision_count": 3}) == "approve"

    def test_above_max_routes_to_approve(self):
        assert after_revision({"revision_count": 5}) == "approve"

    def test_zero_revisions_routes_to_review(self):
        assert after_revision({"revision_count": 0}) == "review"


# ---------------------------------------------------------------------------
# Resume state builder
# ---------------------------------------------------------------------------


class TestBuildResumeState:
    def test_revision_resume(self):
        result = _build_resume_state("revision", {"feedback": "Add temperature check"})
        assert result["status"] == "revision_requested"
        assert result["revision_feedback"] == "Add temperature check"

    def test_output_resume(self):
        result = _build_resume_state("output", {"timestamp": "2026-02-26T10:00:00Z"})
        assert result["status"] == "approved"
        assert result["approval_timestamp"] == "2026-02-26T10:00:00Z"

    def test_unknown_resume_returns_empty(self):
        assert _build_resume_state("unknown", {}) == {}

    def test_revision_missing_feedback_defaults_to_empty_string(self):
        result = _build_resume_state("revision", {})
        assert result["revision_feedback"] == ""


# ---------------------------------------------------------------------------
# Graph compilation
# ---------------------------------------------------------------------------


class TestCreateAgentGraph:
    def test_graph_compiles_without_error(self):
        graph = create_agent_graph()
        assert graph is not None


# ---------------------------------------------------------------------------
# Intent node (mocked LLM)
# ---------------------------------------------------------------------------


class TestIntentNode:
    @pytest.mark.asyncio
    async def test_generate_twi_intent(self):
        with patch(
            "app.agent.nodes.intent.call_llm",
            new=AsyncMock(return_value=("generate_twi", 10)),
        ):
            from app.agent.nodes.intent import intent_node

            result = await intent_node(_make_state())
        assert result["intent"] == "generate_twi"

    @pytest.mark.asyncio
    async def test_invalid_llm_response_defaults_to_unknown(self):
        with patch(
            "app.agent.nodes.intent.call_llm",
            new=AsyncMock(return_value=("gibberish", 10)),
        ):
            from app.agent.nodes.intent import intent_node

            result = await intent_node(_make_state())
        assert result["intent"] == "unknown"

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "intent", ["generate_twi", "edit_twi", "question", "unknown"]
    )
    async def test_all_valid_intents_pass_through(self, intent):
        with patch(
            "app.agent.nodes.intent.call_llm", new=AsyncMock(return_value=(intent, 10))
        ):
            from app.agent.nodes.intent import intent_node

            result = await intent_node(_make_state())
        assert result["intent"] == intent


# ---------------------------------------------------------------------------
# Revision node
# ---------------------------------------------------------------------------


class TestReviseNode:
    @pytest.mark.asyncio
    async def test_revision_increments_count(self):
        from app.agent.nodes.revise import revise_node

        result = await revise_node(_make_state(revision_count=1))
        assert result["revision_count"] == 2
        assert result["status"] == "revision_requested"

    @pytest.mark.asyncio
    async def test_first_revision_sets_count_to_one(self):
        from app.agent.nodes.revise import revise_node

        result = await revise_node(_make_state())
        assert result["revision_count"] == 1
