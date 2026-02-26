import uuid
import logging
from datetime import datetime, timezone

from app.agent.state import AgentState
from app.agent.tools.pdf_generator import generate_twi_pdf, _extract_title
from app.services.blob_storage import upload_pdf
from app.services.cosmos_db import DocumentStore

logger = logging.getLogger(__name__)


async def output_node(state: AgentState) -> AgentState:
    """Generate the TWI PDF and upload it to Blob Storage."""
    pdf_bytes = await generate_twi_pdf(
        content=state["draft"],
        metadata=state.get("draft_metadata", {}),
        user_id=state["user_id"],
        approval_timestamp=state.get("approval_timestamp"),
    )

    blob_name = f"twi/{state['conversation_id']}/{uuid.uuid4().hex}.pdf"
    pdf_url = await upload_pdf(pdf_bytes, blob_name)
    logger.info("PDF generated and uploaded: blob_name=%s", blob_name)

    title = _extract_title(state["draft"])

    doc_store = DocumentStore()
    await doc_store.save({
        "document_id": uuid.uuid4().hex,
        "conversation_id": state["conversation_id"],
        "user_id": state["user_id"],
        "tenant_id": state.get("tenant_id", "poc-tenant"),
        "title": title,
        "content_type": "twi",
        "draft_content": state["draft"],
        "pdf_blob_name": blob_name,
        "pdf_url": pdf_url,
        "llm_model": state.get("draft_metadata", {}).get("model", "mistral-large-latest"),
        "revision_count": state.get("revision_count", 0),
        "status": "approved",
        "approved_at": state.get("approval_timestamp") or datetime.now(timezone.utc).isoformat(),
        "approved_by": state["user_id"]
    })
    logger.info("Document saved to Cosmos DB: conversation_id=%s", state["conversation_id"])

    return {
        **state,
        "title": title,
        "pdf_url": pdf_url,
        "pdf_blob_name": blob_name,
        "status": "completed",
    }
