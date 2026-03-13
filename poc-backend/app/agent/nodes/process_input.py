import json
import logging
import re

from app.agent.state import AgentState
from app.services.ai_foundry import call_llm

logger = logging.getLogger(__name__)

MACHINE_PATTERN = re.compile(r"(?:gep|machine|cnc)\s*([A-Z0-9\-]+)", re.IGNORECASE)
PROCESS_TYPE_PATTERN = re.compile(
    r"(?:karbantartas|maintenance|beallitas|setup|ellenorzes|check|javitas|repair|mukodtetes|operation)\b",
    re.IGNORECASE,
)

_EXTRACTION_SYSTEM_PROMPT = (
    "Te egy strukturált adatkinyerő modul vagy.\n"
    "A felhasználó TWI (Training Within Industry) munkautasítást kér.\n\n"
    "Feladatod: a szabad szövegből kinyerni a következő mezőket JSON-ben:\n"
    "- machine_id: gép/eszköz azonosító (null ha nem található)\n"
    "- process_type: a folyamat típusa (pl. maintenance, setup, check, repair, operation; null ha nem egyértelmű)\n"
    "- department: üzem / osztály neve (null ha nem található)\n"
    "- safety_concerns: biztonsági vonatkozások listája (üres lista ha nincs)\n"
    "- summary: a kérés egy mondatos összefoglalása\n\n"
    "VÁLASZOLJ KIZÁRÓLAG valid JSON-nel, semmi mással.\n"
    "Példa:\n"
    '{"machine_id": "CNC-01", "process_type": "maintenance", '
    '"department": null, "safety_concerns": ["forró felületek"], '
    '"summary": "CNC-01 gép napi karbantartási utasítás"}'
)

_EXTRACTION_PROMPT = "Felhasználó üzenete: {message}"


def _regex_extract(message: str) -> dict:
    """Fast-path extraction using regex patterns."""
    machine_match = MACHINE_PATTERN.search(message)
    process_types = PROCESS_TYPE_PATTERN.findall(message)
    return {
        "extracted_machine_id": machine_match.group(1) if machine_match else None,
        "process_types": process_types if process_types else None,
    }


async def _llm_extract(message: str) -> tuple[dict, int, int]:
    """LLM-based structured extraction. Returns (fields_dict, in_tokens, out_tokens)."""
    response, in_tokens, out_tokens = await call_llm(
        system_prompt=_EXTRACTION_SYSTEM_PROMPT,
        prompt=_EXTRACTION_PROMPT.format(message=message),
        temperature=0.1,
        max_tokens=300,
    )
    try:
        parsed = json.loads(response.strip())
    except (json.JSONDecodeError, ValueError):
        logger.warning("LLM extraction returned non-JSON: %.100s", response)
        parsed = {}
    return parsed, in_tokens, out_tokens


async def process_input_node(state: AgentState) -> AgentState:
    """Structure and validate the user's TWI generation request.

    Uses regex for fast extraction and LLM for richer structured extraction.
    Falls back gracefully to regex-only if LLM is unavailable.
    """
    message = state.get("message", "")

    regex_fields = _regex_extract(message)

    llm_fields: dict = {}
    extra_in = 0
    extra_out = 0
    try:
        llm_fields, extra_in, extra_out = await _llm_extract(message)
    except Exception as exc:
        logger.warning("LLM extraction failed, using regex only: %s", exc)

    processed = {
        "original_message": message,
        "intent": state.get("intent"),
        "channel": state.get("channel"),
        "extracted_machine_id": (
            llm_fields.get("machine_id") or regex_fields.get("extracted_machine_id")
        ),
        "process_types": (
            [llm_fields["process_type"]]
            if llm_fields.get("process_type")
            else regex_fields.get("process_types")
        ),
        "department": llm_fields.get("department"),
        "safety_concerns": llm_fields.get("safety_concerns", []),
        "summary": llm_fields.get("summary"),
    }

    current_in = state.get("llm_tokens_input") or 0
    current_out = state.get("llm_tokens_output") or 0

    return {
        **state,
        "processed_input": processed,
        "llm_tokens_input": current_in + extra_in,
        "llm_tokens_output": current_out + extra_out,
    }
