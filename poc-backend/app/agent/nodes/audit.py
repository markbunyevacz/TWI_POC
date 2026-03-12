import logging
from datetime import datetime, timezone

from app.agent.state import AgentState
from app.services.cosmos_db import AuditStore

logger = logging.getLogger(__name__)

_STATUS_TO_EVENT = {
    "completed": "twi_generated",
    "rejected": "twi_rejected",
}


async def audit_node(state: AgentState) -> AgentState:
    """Write an immutable audit log entry to Cosmos DB (EU AI Act compliance)."""
    try:
        event_type = _STATUS_TO_EVENT.get(state.get("status", ""), "twi_generated")
        audit_store = AuditStore()
        await audit_store.log(
            {
                "conversation_id": state["conversation_id"],
                "user_id": state["user_id"],
                "tenant_id": state["tenant_id"],
                "channel": state["channel"],
                "event_type": event_type,
                "intent": state.get("intent"),
                "llm_model": state.get("llm_model"),
                "llm_tokens_input": state.get("llm_tokens_input"),
                "llm_tokens_output": state.get("llm_tokens_output"),
                "revision_count": state.get("revision_count", 0),
                "pdf_blob_name": state.get("pdf_blob_name"),
                "status": state["status"],
                "approval_timestamp": state.get("approval_timestamp"),
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
        )
    except Exception as exc:
        # Audit failure must not prevent the user from receiving their PDF result.
        # Log the failure loudly so ops can investigate.
        logger.error(
            "Audit log write failed (conversation_id=%s): %s",
            state.get("conversation_id"),
            exc,
            exc_info=True,
        )
    return state
