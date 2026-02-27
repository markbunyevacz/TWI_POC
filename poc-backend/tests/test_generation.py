"""Tests for TWI generation node: EU AI Act label, revision context, and output structure."""

import pytest
from unittest.mock import AsyncMock, patch

_LLM_RESPONSE = (
    "## CÍM: CNC-01 gép beállítása\n\n"
    "## CÉL\nA gép megfelelő beállítása a termelés előtt.\n\n"
    "## LÉPÉSEK\n1. Kapcsold be a gépet\n"
)

_BASE_STATE = {
    "user_id": "test-user",
    "tenant_id": "poc-tenant",
    "conversation_id": "conv-001",
    "channel": "msteams",
    "message": "Készíts TWI utasítást a CNC-01 gép beállításáról",
    "intent": "generate_twi",
    "processed_input": {"original_message": "Készíts TWI utasítást"},
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


class TestGenerateNode:
    @pytest.mark.asyncio
    async def test_draft_includes_eu_ai_act_label(self):
        with patch(
            "app.agent.nodes.generate.call_llm",
            new=AsyncMock(return_value=(_LLM_RESPONSE, 50)),
        ):
            from app.agent.nodes.generate import generate_node

            result = await generate_node({**_BASE_STATE})

        assert "⚠️ AI által generált tartalom" in result["draft"]
        assert "emberi felülvizsgálat szükséges" in result["draft"]

    @pytest.mark.asyncio
    async def test_status_set_to_review_needed(self):
        with patch(
            "app.agent.nodes.generate.call_llm",
            new=AsyncMock(return_value=(_LLM_RESPONSE, 50)),
        ):
            from app.agent.nodes.generate import generate_node

            result = await generate_node({**_BASE_STATE})

        assert result["status"] == "review_needed"

    @pytest.mark.asyncio
    async def test_draft_metadata_contains_required_keys(self):
        with patch(
            "app.agent.nodes.generate.call_llm",
            new=AsyncMock(return_value=(_LLM_RESPONSE, 50)),
        ):
            from app.agent.nodes.generate import generate_node

            result = await generate_node({**_BASE_STATE})

        metadata = result["draft_metadata"]
        assert "model" in metadata
        assert "generated_at" in metadata
        assert "revision" in metadata

    @pytest.mark.asyncio
    async def test_llm_model_set_in_state(self):
        with patch(
            "app.agent.nodes.generate.call_llm",
            new=AsyncMock(return_value=(_LLM_RESPONSE, 50)),
        ):
            from app.agent.nodes.generate import generate_node

            result = await generate_node({**_BASE_STATE})

        assert result["llm_model"] is not None
        assert len(result["llm_model"]) > 0

    @pytest.mark.asyncio
    async def test_revision_context_injected_when_feedback_present(self):
        """When revision_feedback is set, the LLM prompt must include the previous draft."""
        captured: list[dict] = []

        async def mock_llm(prompt, system_prompt=None, temperature=None, max_tokens=None):
            captured.append({"prompt": prompt})
            return _LLM_RESPONSE, 50

        state_with_revision = {
            **_BASE_STATE,
            "draft": "old draft content",
            "revision_feedback": "Add temperature check to step 3",
            "revision_count": 1,
        }

        with patch("app.agent.nodes.generate.call_llm", new=mock_llm):
            from app.agent.nodes.generate import generate_node

            await generate_node(state_with_revision)

        prompt_text = captured[0]["prompt"]
        assert "old draft content" in prompt_text
        assert "Add temperature check" in prompt_text

    @pytest.mark.asyncio
    async def test_revision_count_preserved_in_metadata(self):
        state = {**_BASE_STATE, "revision_count": 2}
        with patch(
            "app.agent.nodes.generate.call_llm",
            new=AsyncMock(return_value=(_LLM_RESPONSE, 50)),
        ):
            from app.agent.nodes.generate import generate_node

            result = await generate_node(state)

        assert result["draft_metadata"]["revision"] == 2

    @pytest.mark.asyncio
    async def test_draft_content_contains_llm_response(self):
        with patch(
            "app.agent.nodes.generate.call_llm",
            new=AsyncMock(return_value=(_LLM_RESPONSE, 50)),
        ):
            from app.agent.nodes.generate import generate_node

            result = await generate_node({**_BASE_STATE})

        assert "CNC-01" in result["draft"]

    @pytest.mark.asyncio
    async def test_temperature_is_0_3_for_generation(self):
        """Generation must use temperature=0.3 per EU AI Act rule."""
        captured: list = []

        async def mock_llm(prompt, system_prompt=None, temperature=None, max_tokens=None):
            captured.append(temperature)
            return _LLM_RESPONSE, 50

        with patch("app.agent.nodes.generate.call_llm", new=mock_llm):
            from app.agent.nodes.generate import generate_node

            await generate_node({**_BASE_STATE})

        assert captured[0] == 0.3


class TestIntentNodeTemperature:
    @pytest.mark.asyncio
    async def test_intent_uses_low_temperature(self):
        """Intent classification must use temperature=0.1."""
        captured: list = []

        async def mock_llm(prompt, system_prompt=None, temperature=None, max_tokens=None):
            captured.append(temperature)
            return "generate_twi", 10

        with patch("app.agent.nodes.intent.call_llm", new=mock_llm):
            from app.agent.nodes.intent import intent_node

            await intent_node({**_BASE_STATE})

        assert captured[0] == 0.1


class TestProcessInputNode:
    @pytest.mark.asyncio
    async def test_processed_input_includes_original_message(self):
        from app.agent.nodes.process_input import process_input_node

        result = await process_input_node({**_BASE_STATE})
        assert result["processed_input"]["original_message"] == _BASE_STATE["message"]

    @pytest.mark.asyncio
    async def test_processed_input_includes_channel(self):
        from app.agent.nodes.process_input import process_input_node

        result = await process_input_node({**_BASE_STATE})
        assert result["processed_input"]["channel"] == "msteams"


class TestAdaptiveCards:
    def test_review_card_contains_eu_ai_act_label(self):
        from app.bot.adaptive_cards import create_review_card

        card = create_review_card(
            draft="⚠️ AI által generált tartalom — emberi felülvizsgálat szükséges.",
            metadata={"model": "mistral-large-latest", "generated_at": "2026-02-26"},
        )
        assert "AI által generált tartalom" in str(card)

    def test_review_card_has_three_actions(self):
        from app.bot.adaptive_cards import create_review_card

        card = create_review_card(draft="test", metadata={})
        assert len(card["actions"]) == 3

    def test_review_card_draft_truncated_to_2000(self):
        from app.bot.adaptive_cards import create_review_card

        long_draft = "x" * 5000
        card = create_review_card(draft=long_draft, metadata={})
        draft_block = next(
            b
            for b in card["body"]
            if b.get("type") == "TextBlock" and "x" * 10 in b.get("text", "")
        )
        assert len(draft_block["text"]) <= 2000

    def test_approval_card_has_two_actions(self):
        from app.bot.adaptive_cards import create_approval_card

        card = create_approval_card(draft="test", metadata={})
        assert len(card["actions"]) == 2

    def test_result_card_has_download_action(self):
        from app.bot.adaptive_cards import create_result_card

        card = create_result_card(
            pdf_url="https://example.com/test.pdf",
            document_title="CNC-01 TWI",
            metadata={"model": "mistral-large-latest"},
        )
        action = card["actions"][0]
        assert action["type"] == "Action.OpenUrl"
        assert action["url"] == "https://example.com/test.pdf"

    def test_welcome_card_schema_version(self):
        from app.bot.adaptive_cards import create_welcome_card

        card = create_welcome_card()
        assert card["$schema"] == "http://adaptivecards.io/schemas/adaptive-card.json"
        assert card["version"] == "1.4"
