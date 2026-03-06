import logging
from datetime import datetime, timezone

from app.agent.state import AgentState
from app.services.cosmos_db import AuditStore

logger = logging.getLogger(__name__)


async def audit_node(state: AgentState) -> AgentState:
    """Write an immutable audit log entry to Cosmos DB (EU AI Act compliance)."""
    try:
        audit_store = AuditStore()
        await audit_store.log(
            {
                "conversation_id": state["conversation_id"],
                "user_id": state["user_id"],
                "tenant_id": state["tenant_id"],
                "channel": state["channel"],
                "event_type": "twi_generated",
                "intent": state.get("intent"),
                "llm_model": state.get("llm_model"),
                "llm_tokens_used": state.get("llm_tokens_used"),
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
