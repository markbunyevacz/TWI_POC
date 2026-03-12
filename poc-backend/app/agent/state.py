from typing import Any, Optional
from typing_extensions import TypedDict


class AgentState(TypedDict):
    # Input context
    user_id: str
    tenant_id: str
    conversation_id: str
    channel: str          # "msteams" | "telegram"
    message: str

    # Processing
    intent: Optional[str]          # "generate_twi" | "edit_twi" | "question" | "unknown"
    processed_input: Optional[dict]
    draft: Optional[str]
    draft_metadata: Optional[dict]  # {model, generated_at, revision}

    # Revision loop
    revision_feedback: Optional[str]
    revision_count: int

    # Output
    status: str  # "processing" | "review_needed" | "revision_requested" | "approved" | "completed" | "error"
    pdf_url: Optional[str]
    pdf_blob_name: Optional[str]

    # Audit / telemetry
    llm_model: Optional[str]
    llm_tokens_used: Optional[int]
    approval_timestamp: Optional[str]

    # Message history (LangGraph internal)
    messages: list[Any]
