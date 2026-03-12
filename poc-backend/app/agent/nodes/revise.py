import logging
from datetime import datetime, timezone

from app.agent.state import AgentState
from app.services.cosmos_db import AuditStore

logger = logging.getLogger(__name__)


async def revise_node(state: AgentState) -> AgentState:
    """Increment the revision counter and carry user feedback into the next generate cycle."""
    revision_count = state.get("revision_count", 0) + 1

    try:
        audit_store = AuditStore()
        await audit_store.log(
            {
                "conversation_id": state["conversation_id"],
                "user_id": state["user_id"],
                "tenant_id": state["tenant_id"],
                "channel": state["channel"],
                "event_type": "twi_revised",
                "intent": state.get("intent"),
                "llm_model": state.get("llm_model"),
                "llm_tokens_input": state.get("llm_tokens_input"),
                "llm_tokens_output": state.get("llm_tokens_output"),
                "revision_count": revision_count,
                "status": "revision_requested",
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
        )
    except Exception as exc:
        logger.error(
            "Revision audit log failed (conversation_id=%s): %s",
            state.get("conversation_id"),
            exc,
            exc_info=True,
        )

    return {
        **state,
        "revision_count": revision_count,
        "status": "revision_requested",
    }
