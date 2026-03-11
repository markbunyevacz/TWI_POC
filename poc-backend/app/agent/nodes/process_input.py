"""Process and structure the user's TWI generation or edit request.

Extracts structured fields (machine name, process type, safety category)
from the raw user message via simple keyword matching.  For ``edit_twi``
intent, queries Cosmos DB for the most recent document in the conversation
so the generate node can use it as revision context.
"""

import logging
import re
from typing import Optional

from app.agent.state import AgentState

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Lightweight keyword extractors (no LLM call required)
# ---------------------------------------------------------------------------

_MACHINE_PATTERN = re.compile(
    r"\b([A-Z]{1,6}[\-\s]?\d{1,4}[A-Z]?)\b"  # e.g. CNC-01, ABC123, PLC 2
)

_SAFETY_KEYWORDS: dict[str, str] = {
    "forró": "heat_hazard",
    "hő": "heat_hazard",
    "magas nyomás": "pressure_hazard",
    "nyomás": "pressure_hazard",
    "vegyszer": "chemical_hazard",
    "kémiai": "chemical_hazard",
    "áram": "electrical_hazard",
    "elektromos": "electrical_hazard",
    "éles": "cut_hazard",
    "vágó": "cut_hazard",
    "magasban": "fall_hazard",
    "sugárzás": "radiation_hazard",
}

_PROCESS_KEYWORDS: dict[str, str] = {
    "beállítás": "setup",
    "karbantartás": "maintenance",
    "tisztítás": "cleaning",
    "javítás": "repair",
    "ellenőrzés": "inspection",
    "indítás": "startup",
    "leállítás": "shutdown",
    "csere": "replacement",
    "szerelés": "assembly",
    "kalibráció": "calibration",
    "kalibrálás": "calibration",
}


def _extract_machine_name(text: str) -> Optional[str]:
    """Extract a machine/equipment identifier from the message."""
    match = _MACHINE_PATTERN.search(text)
    return match.group(1) if match else None


def _extract_safety_categories(text: str) -> list[str]:
    """Return a list of safety categories mentioned in the message."""
    lower = text.lower()
    found: list[str] = []
    for keyword, category in _SAFETY_KEYWORDS.items():
        if keyword in lower and category not in found:
            found.append(category)
    return found


def _extract_process_type(text: str) -> Optional[str]:
    """Return the most likely process type based on keywords."""
    lower = text.lower()
    for keyword, process_type in _PROCESS_KEYWORDS.items():
        if keyword in lower:
            return process_type
    return None


async def _fetch_existing_document(conversation_id: str) -> Optional[dict]:
    """For edit_twi intent, fetch the latest document from this conversation.

    Returns ``None`` if no document is found or if the DB is unavailable.
    """
    try:
        from app.services.cosmos_db import DocumentStore

        store = DocumentStore()
        doc = await store.collection.find_one(
            {"conversation_id": conversation_id},
            sort=[("created_at", -1)],
        )
        return doc
    except Exception as exc:
        logger.warning("Could not fetch existing document for edit: %s", exc)
        return None


async def process_input_node(state: AgentState) -> AgentState:
    """Structure and validate the user's TWI generation request.

    Extracts machine name, process type, and safety categories from the
    raw message.  For ``edit_twi`` intent, also fetches the previous
    document from Cosmos DB to provide revision context.
    """
    message = state["message"]
    intent = state.get("intent")

    processed: dict = {
        "original_message": message,
        "intent": intent,
        "channel": state.get("channel"),
        "machine_name": _extract_machine_name(message),
        "process_type": _extract_process_type(message),
        "safety_categories": _extract_safety_categories(message),
    }

    # For edit_twi: attach existing document content as context
    if intent == "edit_twi":
        existing = await _fetch_existing_document(state["conversation_id"])
        if existing:
            processed["existing_document"] = {
                "title": existing.get("title", ""),
                "draft_content": existing.get("draft_content", ""),
                "revision_count": existing.get("revision_count", 0),
            }
            logger.info(
                "Found existing document for edit: title=%s",
                existing.get("title"),
            )
        else:
            logger.info(
                "No existing document found for conversation=%s — "
                "will generate as new.",
                state["conversation_id"],
            )

    return {**state, "processed_input": processed}
