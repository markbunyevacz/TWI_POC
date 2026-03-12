"""Tests for the LangGraph agent graph: routing, revision loop, and state transitions."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.agent.graph import (
    should_generate,
    after_review,
    after_revision,
    create_agent_graph,
    run_agent,
    reject_node,
    _build_resume_state,
)
from app.agent.nodes.audit import _resolve_event_type
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

    def test_rejected_routes_to_reject(self):
        assert after_review({"status": "rejected"}) == "reject"

    def test_unknown_status_routes_to_reject(self):
        assert after_review({"status": "something_else"}) == "reject"


class TestAfterRevision:
    def test_below_max_routes_to_regenerate(self):
        assert after_revision({"revision_count": 1}) == "regenerate"

    def test_at_max_routes_to_approve(self):
        assert after_revision({"revision_count": 3}) == "approve"

    def test_above_max_routes_to_approve(self):
        assert after_revision({"revision_count": 5}) == "approve"

    def test_zero_revisions_routes_to_regenerate(self):
        assert after_revision({"revision_count": 0}) == "regenerate"


# ---------------------------------------------------------------------------
# Audit event_type resolution
# ---------------------------------------------------------------------------


class TestResolveEventType:
    def test_completed_maps_to_twi_generated(self):
        assert _resolve_event_type("completed") == "twi_generated"

    def test_approved_maps_to_twi_approved(self):
        assert _resolve_event_type("approved") == "twi_approved"

    def test_rejected_maps_to_twi_rejected(self):
        assert _resolve_event_type("rejected") == "twi_rejected"

    def test_revision_requested_maps_to_twi_revised(self):
        assert _resolve_event_type("revision_requested") == "twi_revised"

    def test_unknown_status_defaults_to_twi_generated(self):
        assert _resolve_event_type("processing") == "twi_generated"


# ---------------------------------------------------------------------------
# Reject node
# ---------------------------------------------------------------------------


class TestRejectNode:
    @pytest.mark.asyncio
    async def test_sets_rejected_status(self):
        result = await reject_node(_make_state(status="approved"))
        assert result["status"] == "rejected"


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

    def test_unknown_resume_raises_value_error(self):
        with pytest.raises(ValueError, match="Unknown resume_from"):
            _build_resume_state("unknown", {})

    def test_revision_missing_feedback_defaults_to_empty_string(self):
        result = _build_resume_state("revision", {})
        assert result["revision_feedback"] == ""

    def test_rejection_resume(self):
        result = _build_resume_state("rejection", {})
        assert result["status"] == "rejected"


# ---------------------------------------------------------------------------
# Graph compilation
# ---------------------------------------------------------------------------


class TestCreateAgentGraph:
    @pytest.mark.asyncio
    async def test_graph_compiles_without_error(self):
        graph = await create_agent_graph()
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


# ---------------------------------------------------------------------------
# run_agent — as_node passthrough
# ---------------------------------------------------------------------------


class TestRunAgentAsNode:
    """Verify that run_agent forwards the as_node parameter to aupdate_state."""

    def _mock_graph(self, return_state: dict | None = None):
        graph = MagicMock()
        graph.aupdate_state = AsyncMock()
        graph.ainvoke = AsyncMock(return_value=return_state or _make_state())
        return graph

    @pytest.mark.asyncio
    async def test_as_node_forwarded_to_aupdate_state(self):
        graph = self._mock_graph()
        await run_agent(
            graph,
            message="",
            user_id="u1",
            conversation_id="c1",
            resume_from="revision",
            context={"feedback": "fix step 3"},
            as_node="review",
        )

        graph.aupdate_state.assert_called_once()
        _, kwargs = graph.aupdate_state.call_args
        assert kwargs["as_node"] == "review"

    @pytest.mark.asyncio
    async def test_as_node_defaults_to_none(self):
        graph = self._mock_graph()
        await run_agent(
            graph,
            message="",
            user_id="u1",
            conversation_id="c1",
            resume_from="revision",
            context={"feedback": "minor tweak"},
        )

        graph.aupdate_state.assert_called_once()
        _, kwargs = graph.aupdate_state.call_args
        assert kwargs["as_node"] is None

    @pytest.mark.asyncio
    async def test_as_node_ignored_for_new_conversation(self):
        graph = self._mock_graph()
        await run_agent(
            graph,
            message="Készíts TWI utasítást",
            user_id="u1",
            conversation_id="c1",
            as_node="review",
        )

        graph.aupdate_state.assert_not_called()
        graph.ainvoke.assert_called_once()
