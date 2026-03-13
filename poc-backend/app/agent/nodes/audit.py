import logging
from datetime import datetime, timezone

from app.agent.state import AgentState
from app.services.cosmos_db import AuditStore

logger = logging.getLogger(__name__)

_STATUS_TO_EVENT_TYPE: dict[str, str] = {
    "completed": "twi_generated",
    "approved": "twi_approved",
    "rejected": "twi_rejected",
    "revision_requested": "twi_revised",
}


def _resolve_event_type(status: str) -> str:
    """Map agent status to the corresponding audit event_type."""
    return _STATUS_TO_EVENT_TYPE.get(status, "twi_generated")


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
                "event_type": _resolve_event_type(state.get("status", "")),
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
        logger.error(
            "Audit log write failed (conversation_id=%s): %s",
            state.get("conversation_id"),
            exc,
            exc_info=True,
        )
    return state
