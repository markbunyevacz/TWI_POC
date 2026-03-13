"""LLM-based clarification node for unknown or ambiguous user intents."""

import logging

from app.agent.state import AgentState
from app.services.ai_foundry import call_llm

logger = logging.getLogger(__name__)

_CLARIFY_SYSTEM_PROMPT = (
    "Te az agentize.eu AI platform segítő modulja vagy.\n"
    "A felhasználó üzenete nem volt egyértelműen besorolható.\n\n"
    "FELADATOD:\n"
    "Készíts egy rövid, barátságos visszakérdezést, amely segít "
    "megérteni, mit szeretne a felhasználó. Adj konkrét példákat "
    "az elérhető funkciókra:\n"
    "- TWI (Training Within Industry) munkautasítás generálása\n"
    "- Meglévő TWI szerkesztése / módosítása\n"
    "- Kérdés a rendszerről vagy a folyamatokról\n\n"
    "SZABÁLYOK:\n"
    "- Magyar nyelven válaszolj\n"
    "- Légy tömör (max 3–4 mondat)\n"
    "- Adj 1–2 konkrét példát arra, mit írhat a felhasználó\n"
    "- NE generálj TWI tartalmat, csak kérdezz vissza\n"
)

_CLARIFY_PROMPT = "A felhasználó üzenete: {message}"


async def clarify_node(state: AgentState) -> AgentState:
    """Generate an intelligent clarification response for unknown intents via LLM."""
    try:
        response, in_tokens, out_tokens = await call_llm(
            system_prompt=_CLARIFY_SYSTEM_PROMPT,
            prompt=_CLARIFY_PROMPT.format(message=state["message"]),
            temperature=0.3,
            max_tokens=300,
        )

        current_in = state.get("llm_tokens_input") or 0
        current_out = state.get("llm_tokens_output") or 0

        return {
            **state,
            "status": "clarification_needed",
            "draft": response.strip(),
            "llm_tokens_input": current_in + in_tokens,
            "llm_tokens_output": current_out + out_tokens,
        }
    except Exception as exc:  # noqa: BLE001
        logger.error("Clarification LLM call failed: %s", exc, exc_info=True)
        return {
            **state,
            "status": "clarification_needed",
            "draft": None,
        }
