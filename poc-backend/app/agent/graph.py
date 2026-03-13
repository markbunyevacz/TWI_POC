import logging

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from app.agent.state import AgentState
from app.agent.nodes.intent import intent_node
from app.agent.nodes.process_input import process_input_node
from app.agent.nodes.generate import generate_node
from app.agent.nodes.review import review_node
from app.agent.nodes.revise import revise_node
from app.agent.nodes.approve import approve_node
from app.agent.nodes.output import output_node
from app.agent.nodes.audit import audit_node
from app.agent.nodes.clarify import clarify_node

logger = logging.getLogger(__name__)

# Singleton compiled graph
_graph = None
_checkpointer = None


async def _get_checkpointer():
    """Get or create the checkpointer - MongoDB if available, else Memory."""
    global _checkpointer
    if _checkpointer is None:
        # Try to use MongoDB checkpointer for persistence
        try:
            from app.agent.mongodb_checkpointer import create_mongodb_checkpointer

            # Check if Cosmos connection is configured
            from app.config import settings

            if settings.cosmos_connection:
                _checkpointer = await create_mongodb_checkpointer()
                logger.info("Using MongoDB checkpointer for persistent state")
            else:
                logger.warning(
                    "Cosmos DB not configured — using in-memory checkpointer. "
                    "Conversation state will be LOST on restart and is NOT "
                    "shared across replicas. Set COSMOS_CONNECTION to enable persistence."
                )
                _checkpointer = MemorySaver()
        except Exception as exc:
            logger.warning(
                "Failed to initialize MongoDB checkpointer: %s. "
                "Falling back to MemorySaver — state will NOT persist across restarts.",
                exc,
            )
            _checkpointer = MemorySaver()
    return _checkpointer


def should_generate(state: AgentState) -> str:
    """Route after intent classification."""
    intent = state.get("intent", "unknown")
    if intent in ("generate_twi", "edit_twi"):
        return "process_input"
    if intent == "question":
        return "generate"  # Simple Q&A — skip structured input processing
    return "clarify"  # Unknown intent — ask for clarification


def after_review(state: AgentState) -> str:
    """Route after the review human-in-the-loop checkpoint."""
    status = state.get("status", "")
    if status == "approved":
        return "approve"
    if status == "revision_requested":
        return "revise"
    return "reject"


def after_revision(state: AgentState) -> str:
    """Route after revision — hard-cap at 3 revision rounds."""
    if state.get("revision_count", 0) >= 3:
        return "approve"  # Force final approval after max revisions
    return "regenerate"


async def reject_node(state: AgentState) -> AgentState:
    """Finalise rejection state so audit_node logs a twi_rejected event."""
    return {**state, "status": "rejected"}


async def create_agent_graph():
    """Build and compile the LangGraph agent graph."""
    builder = StateGraph(AgentState)

    builder.add_node("classify_intent", intent_node)
    builder.add_node("process_input", process_input_node)
    builder.add_node("generate", generate_node)
    builder.add_node("review", review_node)
    builder.add_node("revise", revise_node)
    builder.add_node("approve", approve_node)
    builder.add_node("output", output_node)
    builder.add_node("audit", audit_node)
    builder.add_node("reject", reject_node)
    builder.add_node("clarify", clarify_node)

    builder.set_entry_point("classify_intent")
    builder.add_conditional_edges(
        "classify_intent",
        should_generate,
        {
            "process_input": "process_input",
            "generate": "generate",
            "clarify": "clarify",
        },
    )
    builder.add_edge("process_input", "generate")
    builder.add_edge("generate", "review")

    builder.add_conditional_edges(
        "review",
        after_review,
        {
            "approve": "approve",
            "revise": "revise",
            "reject": "reject",
        },
    )
    builder.add_edge("reject", "audit")

    builder.add_conditional_edges(
        "revise",
        after_revision,
        {
            "regenerate": "generate",
            "approve": "approve",
        },
    )

    builder.add_edge("approve", "output")
    builder.add_edge("output", "audit")
    builder.add_edge("audit", END)
    builder.add_edge("clarify", END)

    checkpointer = await _get_checkpointer()
    return builder.compile(
        checkpointer=checkpointer,
        interrupt_before=["review", "approve"],
    )


async def get_graph():
    """Return the singleton compiled graph."""
    global _graph
    if _graph is None:
        _graph = await create_agent_graph()
    return _graph


async def run_agent(
    graph,
    message: str,
    user_id: str,
    conversation_id: str,
    channel: str = "msteams",
    tenant_id: str | None = None,
    resume_from: str | None = None,
    context: dict | None = None,
    as_node: str | None = None,
) -> dict:
    """Invoke or resume the LangGraph agent for a given conversation.

    Args:
        tenant_id: Tenant identifier. Falls back to ``settings.default_tenant_id``
            when not provided.
        as_node: Override the ``as_node`` argument passed to
            ``graph.aupdate_state``.  When resuming from the *approval*
            interrupt but routing back to revision, pass ``"review"`` so
            LangGraph evaluates the ``after_review`` conditional edge
            instead of following the static approve → output edge.
    """
    from app.config import settings as _settings

    resolved_tenant_id = tenant_id or _settings.default_tenant_id
    config = {"configurable": {"thread_id": conversation_id}}

    if resume_from:
        state_update = _build_resume_state(resume_from, context or {})
        # Update the existing checkpoint state, then resume from it.
        # Passing None to ainvoke tells LangGraph to continue from the
        # last interrupt rather than starting a new run.
        await graph.aupdate_state(config, state_update, as_node=as_node)
        result = await graph.ainvoke(None, config)
    else:
        initial_state = AgentState(
            user_id=user_id,
            tenant_id=resolved_tenant_id,
            conversation_id=conversation_id,
            channel=channel,
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
            llm_tokens_input=None,
            llm_tokens_output=None,
            approval_timestamp=None,
            messages=[],
        )
        result = await graph.ainvoke(initial_state, config)

    # Normalise: ainvoke returns AddableValuesDict (a dict subclass) or
    # occasionally a snapshot object with a .values property.
    if not isinstance(result, dict):
        if hasattr(result, "values") and not callable(result.values):
            result = result.values
        else:
            result = {}

    return result


def _build_resume_state(resume_from: str, context: dict) -> dict:
    """Build the state patch to resume after a human-in-the-loop interrupt.

    Raises:
        ValueError: If ``resume_from`` is not a recognised resume point.
    """
    if resume_from == "revision":
        return {
            "status": "revision_requested",
            "revision_feedback": context.get("feedback", ""),
        }
    if resume_from == "output":
        return {
            "status": "approved",
            "approval_timestamp": context.get("timestamp"),
        }
    if resume_from == "rejection":
        return {
            "status": "rejected",
        }
    raise ValueError(
        f"Unknown resume_from value: {resume_from!r}. "
        "Expected 'revision', 'output', or 'rejection'."
    )
