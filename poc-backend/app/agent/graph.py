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

logger = logging.getLogger(__name__)

# Singleton compiled graph (PoC: in-memory checkpointer)
_graph = None


def should_generate(state: AgentState) -> str:
    """Route after intent classification."""
    intent = state.get("intent", "unknown")
    if intent in ("generate_twi", "edit_twi"):
        return "process_input"
    if intent == "question":
        return "generate"   # Simple Q&A — skip structured input processing
    return "clarify"        # Unknown intent — ask for clarification


def after_review(state: AgentState) -> str:
    """Route after the review human-in-the-loop checkpoint."""
    status = state.get("status", "")
    if status == "approved":
        return "approve"
    if status == "revision_requested":
        return "revise"
    return END  # rejected


def after_revision(state: AgentState) -> str:
    """Route after revision — hard-cap at 3 revision rounds."""
    if state.get("revision_count", 0) >= 3:
        return "approve"   # Force final approval after max revisions
    return "regenerate"


async def clarify_node(state: AgentState) -> AgentState:
    """Placeholder clarification node for unknown intent."""
    return {
        **state,
        "status": "clarification_needed",
        "draft": None,
    }


def create_agent_graph():
    """Build and compile the LangGraph agent graph."""
    builder = StateGraph(AgentState)

    builder.add_node("intent", intent_node)
    builder.add_node("process_input", process_input_node)
    builder.add_node("generate", generate_node)
    builder.add_node("review", review_node)
    builder.add_node("revise", revise_node)
    builder.add_node("approve", approve_node)
    builder.add_node("output", output_node)
    builder.add_node("audit", audit_node)
    builder.add_node("clarify", clarify_node)

    builder.set_entry_point("intent")
    builder.add_conditional_edges(
        "intent",
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
            END: END,
        },
    )

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

    checkpointer = MemorySaver()
    return builder.compile(
        checkpointer=checkpointer,
        interrupt_before=["review", "approve"],
    )


def get_graph():
    """Return the singleton compiled graph."""
    global _graph
    if _graph is None:
        _graph = create_agent_graph()
    return _graph


async def run_agent(
    graph,
    message: str,
    user_id: str,
    conversation_id: str,
    channel: str = "msteams",
    tenant_id: str = "poc-tenant",
    resume_from: str | None = None,
    context: dict | None = None,
) -> dict:
    """Invoke or resume the LangGraph agent for a given conversation."""
    config = {"configurable": {"thread_id": conversation_id}}

    if resume_from:
        state_update = _build_resume_state(resume_from, context or {})
        result = await graph.ainvoke(state_update, config)
    else:
        initial_state = AgentState(
            user_id=user_id,
            tenant_id=tenant_id,
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
            llm_tokens_used=None,
            approval_timestamp=None,
            messages=[],
        )
        result = await graph.ainvoke(initial_state, config)

    # Normalise: ainvoke may return state dict or a snapshot object
    if hasattr(result, "values"):
        result = result.values

    return result


def _build_resume_state(resume_from: str, context: dict) -> dict:
    """Build the state patch to resume after a human-in-the-loop interrupt."""
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
    return {}
