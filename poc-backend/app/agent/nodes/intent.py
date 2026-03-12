import logging

from app.agent.state import AgentState
from app.services.ai_foundry import call_llm

logger = logging.getLogger(__name__)

_INTENT_PROMPT = """Te az agentize.eu AI platform intent felismerő modulja vagy.
Osztályozd a felhasználó kérését az alábbi kategóriák egyikébe:

- generate_twi: Új TWI (Training Within Industry) utasítás generálása
- edit_twi: Meglévő TWI szerkesztése, módosítása
- question: Általános kérdés a rendszerről vagy a folyamatokról
- unknown: Nem egyértelmű, kérdezzünk vissza

VÁLASZOLJ KIZÁRÓLAG az intent nevével, semmi mással.

Felhasználó üzenete: {message}"""

_VALID_INTENTS = {"generate_twi", "edit_twi", "question", "unknown"}


async def intent_node(state: AgentState) -> AgentState:
    """Classify user intent using LLM (temperature=0.1 for deterministic output)."""
    try:
        response, in_tokens, out_tokens = await call_llm(
            prompt=_INTENT_PROMPT.format(message=state["message"]),
            temperature=0.1,
            max_tokens=20,
        )
        intent = response.strip().lower()
        if intent not in _VALID_INTENTS:
            intent = "unknown"

        current_in = state.get("llm_tokens_input") or 0
        current_out = state.get("llm_tokens_output") or 0
        return {
            **state,
            "intent": intent,
            "llm_tokens_input": current_in + in_tokens,
            "llm_tokens_output": current_out + out_tokens,
        }
    except Exception as exc:
        logger.error("Intent classification failed: %s", exc, exc_info=True)
        return {**state, "intent": "unknown", "status": "error"}
