from app.agent.state import AgentState
from app.services.ai_foundry import call_llm

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
    response = await call_llm(
        prompt=_INTENT_PROMPT.format(message=state["message"]),
        temperature=0.1,
        max_tokens=20,
    )
    intent = response.strip().lower()
    if intent not in _VALID_INTENTS:
        intent = "unknown"

    return {**state, "intent": intent}
