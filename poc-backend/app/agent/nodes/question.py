"""Q&A node — answers general questions without generating a TWI document."""

import logging

from app.agent.state import AgentState
from app.services.ai_foundry import call_llm

logger = logging.getLogger(__name__)

_QA_SYSTEM_PROMPT = (
    "Te az agentize.eu AI platform kérdés-válasz modulja vagy.\n\n"
    "FELADATOD:\n"
    "A felhasználó kérdésére válaszolsz röviden és informatívan.\n"
    "NEM generálsz TWI munkautasítást — csak kérdésekre válaszolsz.\n\n"
    "SZABÁLYOK:\n"
    "- Válaszolj tömören és pontosan\n"
    "- Ha a kérdés TWI generálásra vonatkozik, irányítsd a felhasználót, "
    "hogy fogalmazza meg konkrétan a kérését (pl. 'Készíts egy TWI utasítást a ...')\n"
    "- Magyar nyelven válaszolj\n"
    "- Technikai szakkifejezéseket angolul is megadhatsz zárójelben\n"
)


async def question_node(state: AgentState) -> AgentState:
    """Answer a general question — does NOT produce a TWI draft."""
    try:
        response, tokens = await call_llm(
            system_prompt=_QA_SYSTEM_PROMPT,
            prompt=state["message"],
            temperature=0.4,
            max_tokens=1000,
        )

        current_tokens = state.get("llm_tokens_used") or 0
        return {
            **state,
            "draft": response,
            "llm_tokens_used": current_tokens + tokens,
            "status": "question_answered",
        }
    except Exception as exc:
        logger.error("Q&A generation failed: %s", exc, exc_info=True)
        return {**state, "status": "error"}
