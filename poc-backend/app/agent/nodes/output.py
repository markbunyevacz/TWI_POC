import uuid
import logging

from app.agent.state import AgentState
from app.agent.tools.pdf_generator import generate_twi_pdf
from app.services.blob_storage import upload_pdf

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

    return {
        **state,
        "pdf_url": pdf_url,
        "pdf_blob_name": blob_name,
        "status": "completed",
    }
