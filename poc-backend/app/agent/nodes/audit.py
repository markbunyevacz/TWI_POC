import logging
from datetime import datetime, timezone

from app.agent.state import AgentState
from app.services.cosmos_db import AuditStore

logger = logging.getLogger(__name__)


async def audit_node(state: AgentState) -> AgentState:
    """Write an immutable audit log entry to Cosmos DB (EU AI Act compliance)."""
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
    return state
