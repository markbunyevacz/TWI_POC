"""End-to-end test for the full LangGraph chat flow.

Exercises the complete path with mocked external services:
  message -> classify_intent -> process_input -> generate -> review (interrupt)
  -> resume with approval -> approve (interrupt) -> resume -> output -> audit -> END

Also tests the revision loop and rejection path.
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from app.agent.graph import create_agent_graph
from app.agent.state import AgentState


def _to_dict(result) -> dict:
    """Normalise graph.ainvoke output to a plain dict."""
    if isinstance(result, dict):
        return result
    return result.values if not callable(result.values) else dict(result)


SAMPLE_DRAFT = (
    "\u26a0\ufe0f AI \u00e1ltal gener\u00e1lt tartalom \u2014 emberi fel\u00fclvizsg\u00e1lat sz\u00fcks\u00e9ges.\n\n"
    "## C\u00cdM: CNC-01 g\u00e9p napi karbantart\u00e1sa\n\n"
    "## C\u00c9L\nA g\u00e9p megfelel\u0151 m\u0171k\u00f6d\u00e9s\u00e9nek biztos\u00edt\u00e1sa.\n\n"
    "## L\u00c9P\u00c9SEK\n1. **F\u0151l\u00e9p\u00e9s:** Kapcsold be a g\u00e9pet\n"
)

CONVERSATION_ID = "e2e-conv-001"


def _initial_state(
    message: str = "K\u00e9sz\u00edts TWI utas\u00edt\u00e1st a CNC-01 g\u00e9p napi karbantart\u00e1s\u00e1r\u00f3l",
) -> dict:
    return AgentState(
        user_id="e2e-user",
        tenant_id="poc-tenant",
        conversation_id=CONVERSATION_ID,
        channel="msteams",
        message=message,
        intent=None,
        processed_input=None,
        draft=None,
        draft_metadata=None,
        revision_feedback=None,
        revision_count=0,
        status="processing",
        pdf_url=None,
        pdf_blob_name=None,
        llm_model=None,
        llm_tokens_used=None,
        approval_timestamp=None,
        messages=[],
    )


@pytest.fixture
def mock_llm():
    """Mock call_llm: first call returns intent, subsequent calls return a draft."""
    call_count = 0

    async def _fake_llm(
        prompt: str, system_prompt=None, temperature=None, max_tokens=None
    ):
        nonlocal call_count
        call_count += 1
        if max_tokens and max_tokens <= 20:
            return ("generate_twi", 10)
        return (SAMPLE_DRAFT, 500)

    with patch("app.agent.nodes.intent.call_llm", side_effect=_fake_llm):
        with patch("app.agent.nodes.generate.call_llm", side_effect=_fake_llm):
            yield


@pytest.fixture
def mock_output_services():
    """Mock PDF generation, blob upload, and Cosmos stores."""
    with patch(
        "app.agent.nodes.output.generate_twi_pdf",
        new=AsyncMock(return_value=b"%PDF-1.4 fake"),
    ) as mock_pdf:
        with patch(
            "app.agent.nodes.output.upload_pdf",
            new=AsyncMock(return_value="https://blob.example.com/twi/test.pdf"),
        ) as mock_blob:
            with patch("app.agent.nodes.output.DocumentStore") as MockDocStore:
                mock_store_instance = MagicMock()
                mock_store_instance.save = AsyncMock(return_value={})
                MockDocStore.return_value = mock_store_instance
                yield mock_pdf, mock_blob, mock_store_instance


@pytest.fixture
def mock_audit():
    """Mock the AuditStore used by audit_node."""
    with patch("app.agent.nodes.audit.AuditStore") as MockAudit:
        mock_instance = MagicMock()
        mock_instance.log = AsyncMock()
        MockAudit.return_value = mock_instance
        yield mock_instance


@pytest.fixture
async def graph():
    """Compile a fresh graph with MemorySaver (no Cosmos dependency)."""
    import app.agent.graph as graph_mod

    old_cp, old_g = graph_mod._checkpointer, graph_mod._graph
    graph_mod._checkpointer = None
    graph_mod._graph = None
    try:
        with patch("app.config.settings") as mock_settings:
            mock_settings.cosmos_connection = ""
            mock_settings.cosmos_database = "test-db"
            mock_settings.ai_model = "gpt-4o"
            g = await create_agent_graph()
            return g
    finally:
        graph_mod._checkpointer = old_cp
        graph_mod._graph = old_g


class TestFullGenerateApproveFlow:
    """Happy path: user sends TWI request -> review -> approve -> PDF output."""

    @pytest.mark.asyncio
    async def test_initial_run_stops_at_review(self, graph, mock_llm):
        config = {"configurable": {"thread_id": CONVERSATION_ID}}
        result = _to_dict(await graph.ainvoke(_initial_state(), config))

        assert result["intent"] == "generate_twi"
        assert result["processed_input"] is not None
        assert result["draft"] is not None
        assert result["status"] == "review_needed"

    @pytest.mark.asyncio
    async def test_full_flow_to_completion(
        self, graph, mock_llm, mock_output_services, mock_audit
    ):
        """Resume from review with 'approved' runs through approve -> output -> audit."""
        config = {"configurable": {"thread_id": "full-flow-001"}}

        result = _to_dict(await graph.ainvoke(_initial_state(), config))
        assert result["status"] == "review_needed"

        await graph.aupdate_state(
            config,
            {"status": "approved", "approval_timestamp": "2026-03-13T10:00:00Z"},
            as_node="review",
        )
        result = _to_dict(await graph.ainvoke(None, config))

        assert result["status"] == "completed"
        assert result["pdf_url"] is not None
        assert "blob.example.com" in result["pdf_url"]

        mock_pdf, mock_blob, mock_doc_store = mock_output_services
        mock_pdf.assert_called_once()
        mock_blob.assert_called_once()
        mock_audit.log.assert_called_once()


class TestRevisionFlow:
    """User requests a revision after reviewing the draft."""

    @pytest.mark.asyncio
    async def test_revision_increments_count_and_regenerates(self, graph, mock_llm):
        config = {"configurable": {"thread_id": "revision-001"}}

        await graph.ainvoke(_initial_state(), config)

        await graph.aupdate_state(
            config,
            {
                "status": "revision_requested",
                "revision_feedback": "Add temperature check step",
            },
            as_node="review",
        )
        result = _to_dict(await graph.ainvoke(None, config))

        assert result["revision_count"] == 1
        assert result["status"] == "review_needed"
        assert result["draft"] is not None


class TestRejectionFlow:
    """User rejects the draft entirely."""

    @pytest.mark.asyncio
    async def test_rejection_goes_to_audit(self, graph, mock_llm, mock_audit):
        config = {"configurable": {"thread_id": "reject-001"}}

        await graph.ainvoke(_initial_state(), config)

        await graph.aupdate_state(
            config,
            {"status": "rejected"},
            as_node="review",
        )
        result = _to_dict(await graph.ainvoke(None, config))

        assert result["status"] == "rejected"
        mock_audit.log.assert_called_once()
        entry = mock_audit.log.call_args[0][0]
        assert entry["event_type"] == "twi_rejected"


class TestClarificationFlow:
    """Unknown intent triggers the clarification path."""

    @pytest.mark.asyncio
    async def test_unknown_intent_returns_clarification(self, graph):
        with patch(
            "app.agent.nodes.intent.call_llm",
            new=AsyncMock(return_value=("unknown", 5)),
        ):
            config = {"configurable": {"thread_id": "clarify-001"}}
            result = _to_dict(
                await graph.ainvoke(_initial_state("valami random szöveg"), config)
            )

        assert result["intent"] == "unknown"
        assert result["status"] == "clarification_needed"
