from datetime import datetime, timezone

from app.agent.state import AgentState
from app.services.ai_foundry import call_llm
from app.config import settings

_TWI_SYSTEM_PROMPT = (  # noqa: E501
    "Te az agentize.eu TWI (Training Within Industry) generátor modulja vagy.\n\n"
    "FELADATOD:\n"
    "A felhasználó inputja alapján strukturált munkautasítást generálsz az alábbi formátumban:\n\n"  # noqa: E501
    "1. CÍM: A munkautasítás rövid címe\n"
    "2. CÉL: Mit ér el a dolgozó, ha követi az utasítást\n"
    "3. SZÜKSÉGES ANYAGOK ÉS ESZKÖZÖK: Felsorolás\n"
    "4. BIZTONSÁGI ELŐÍRÁSOK: Releváns biztonsági figyelmeztetések\n"
    "5. LÉPÉSEK: Számozott lépések, mindegyikhez:\n"
    "   - Főlépés: Mit csinálj\n"
    "   - Kulcspontok: Hogyan csinálj (részletek, amik a minőséget biztosítják)\n"
    "   - Indoklás: Miért fontos ez a lépés\n"
    "6. MINŐSÉGI ELLENŐRZÉS: Hogyan ellenőrizhető a munka minősége\n\n"
    "SZABÁLYOK:\n"
    "- Minden output AUTOMATIKUSAN tartalmazza: "
    '"⚠️ AI által generált tartalom — emberi felülvizsgálat szükséges."\n'
    "- Légy precíz és konkrét — gyártási környezetben használják\n"
    "- Ha nem kapsz elég információt, KÉRDEZZ VISSZA — ne találj ki részleteket\n"
    "- Magyar nyelven válaszolj, technikai szakkifejezések angolul is megadhatók zárójelben\n"
)

_TWI_GENERATE_PROMPT = (
    "A felhasználó kérése:\n"
    "{message}\n\n"
    "{revision_context}\n\n"
    "Generáld a TWI utasítást a megadott formátumban."
)

_EU_AI_ACT_LABEL = (
    "⚠️ AI által generált tartalom — emberi felülvizsgálat szükséges."
)


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


async def generate_node(state: AgentState) -> AgentState:
    """Generate (or revise) a TWI document draft via LLM."""
    revision_context = ""
    if state.get("revision_feedback"):
        revision_context = (
            f"\nKORABBI VÁZLAT:\n{state.get('draft', '')}"
            f"\n\nFELHASZNÁLÓI VISSZAJELZÉS:\n{state['revision_feedback']}"
            f"\n\nMódosítsd a vázlatot a visszajelzés alapján."
        )

    response, tokens = await call_llm(
        system_prompt=_TWI_SYSTEM_PROMPT,
        prompt=_TWI_GENERATE_PROMPT.format(
            message=state["message"],
            revision_context=revision_context,
        ),
        temperature=0.3,
        max_tokens=4000,
    )

    # EU AI Act mandatory label on every AI-generated output
    draft = f"{_EU_AI_ACT_LABEL}\n\n{response}"

    current_tokens = state.get("llm_tokens_used") or 0

    return {
        **state,
        "draft": draft,
        "draft_metadata": {
            "model": settings.ai_model,
            "generated_at": _now_iso(),
            "revision": state.get("revision_count", 0),
        },
        "llm_model": settings.ai_model,
        "llm_tokens_used": current_tokens + tokens,
        "status": "review_needed",
    }
