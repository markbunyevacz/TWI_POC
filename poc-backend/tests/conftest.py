"""Shared pytest fixtures and async test configuration."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.fixture
def mock_llm_response():
    """Default LLM response used in tests that don't need a real LLM."""
    return "generate_twi"


@pytest.fixture
def sample_agent_state():
    """Minimal valid AgentState for unit tests."""
    return {
        "user_id": "test-user-001",
        "tenant_id": "poc-tenant",
        "conversation_id": "conv-test-001",
        "channel": "msteams",
        "message": "Készíts TWI utasítást a CNC-01 gép beállításáról",
        "intent": None,
        "processed_input": None,
        "draft": None,
        "draft_metadata": None,
        "revision_feedback": None,
        "revision_count": 0,
        "status": "processing",
        "pdf_url": None,
        "pdf_blob_name": None,
        "llm_model": None,
        "llm_tokens_used": None,
        "approval_timestamp": None,
        "messages": [],
    }


@pytest.fixture
def sample_draft():
    """A realistic TWI draft for testing downstream nodes."""
    return (
        "⚠️ AI által generált tartalom — emberi felülvizsgálat szükséges.\n\n"
        "## CÍM: CNC-01 gép napi beállítása\n\n"
        "## CÉL\n"
        "A gép megfelelő működésének biztosítása a napi termelés előtt.\n\n"
        "## SZÜKSÉGES ANYAGOK ÉS ESZKÖZÖK\n"
        "- Digitális tolómérő\n"
        "- Kenőolaj\n\n"
        "## BIZTONSÁGI ELŐÍRÁSOK\n"
        "- Gépen dolgozni csak leállított állapotban szabad.\n\n"
        "## LÉPÉSEK\n"
        "1. **Főlépés:** Kapcsold be a gépet\n"
        "   - *Kulcspontok:* Ellenőrizd a főkapcsoló állapotát\n"
        "   - *Indoklás:* A biztonságos indítás megelőzi az áramütést\n\n"
        "## MINŐSÉGI ELLENŐRZÉS\n"
        "Ellenőrizd a gép rezgés szintjét indítás után.\n"
    )
