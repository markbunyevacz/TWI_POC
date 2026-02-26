"""Tests for PDF generation pipeline: output validity, content, and title extraction."""

import pytest
from unittest.mock import patch, MagicMock

from app.agent.tools.pdf_generator import _extract_title, generate_twi_pdf


_SAMPLE_CONTENT = (
    "⚠️ AI által generált tartalom — emberi felülvizsgálat szükséges.\n\n"
    "## CÍM: CNC-01 gép napi beállítása\n\n"
    "## CÉL\n"
    "A gép megfelelő működésének biztosítása.\n\n"
    "## SZÜKSÉGES ANYAGOK ÉS ESZKÖZÖK\n"
    "- Tolómérő\n"
    "- Kenőolaj\n\n"
    "## BIZTONSÁGI ELŐÍRÁSOK\n"
    "Mindig kapcsold le a gépet!\n\n"
    "## LÉPÉSEK\n"
    "1. Ellenőrizd a főkapcsolót\n\n"
    "## MINŐSÉGI ELLENŐRZÉS\n"
    "Mérj rezgést.\n"
)

_METADATA = {
    "model": "mistral-large-latest",
    "generated_at": "2026-02-26 10:00 UTC",
    "revision": 0,
}

_FAKE_PDF = b"%PDF-1.4 fake pdf content for testing"


def _mock_html(html_string: str, collector: list | None = None):
    """Create a WeasyPrint HTML mock that captures rendered HTML."""
    if collector is not None:
        collector.append(html_string)
    mock = MagicMock()
    mock.write_pdf.return_value = _FAKE_PDF
    return mock


# ---------------------------------------------------------------------------
# Title extraction
# ---------------------------------------------------------------------------


class TestExtractTitle:
    def test_extracts_first_non_warning_line(self):
        content = "⚠️ AI label\n\n## CÍM: My Title\nrest"
        assert _extract_title(content) == "CÍM: My Title"

    def test_skips_ai_warning_line(self):
        content = (
            "⚠️ AI által generált tartalom — emberi felülvizsgálat szükséges.\n\n"
            "Real Title"
        )
        assert _extract_title(content) == "Real Title"

    def test_falls_back_to_default_when_no_title(self):
        content = "⚠️ AI által generált tartalom — emberi felülvizsgálat szükséges.\n\n"
        assert _extract_title(content) == "TWI Munkautasítás"

    def test_truncates_long_title_to_100_chars(self):
        assert len(_extract_title("A" * 200)) <= 100

    def test_strips_markdown_heading_prefix(self):
        assert _extract_title("## My Heading") == "My Heading"

    def test_empty_content_returns_default(self):
        assert _extract_title("") == "TWI Munkautasítás"


# ---------------------------------------------------------------------------
# PDF generation (WeasyPrint mocked to avoid system dependencies in CI)
# ---------------------------------------------------------------------------


class TestGenerateTwiPdf:
    @pytest.mark.asyncio
    async def test_returns_bytes(self):
        with patch(
            "app.agent.tools.pdf_generator.HTML",
            side_effect=lambda string: _mock_html(string),
        ):
            result = await generate_twi_pdf(
                content=_SAMPLE_CONTENT,
                metadata=_METADATA,
                user_id="test-user",
            )
        assert isinstance(result, bytes)

    @pytest.mark.asyncio
    async def test_returns_non_empty_bytes(self):
        with patch(
            "app.agent.tools.pdf_generator.HTML",
            side_effect=lambda string: _mock_html(string),
        ):
            result = await generate_twi_pdf(
                content=_SAMPLE_CONTENT,
                metadata=_METADATA,
                user_id="test-user",
            )
        assert len(result) > 0

    @pytest.mark.asyncio
    async def test_pdf_starts_with_pdf_header(self):
        with patch(
            "app.agent.tools.pdf_generator.HTML",
            side_effect=lambda string: _mock_html(string),
        ):
            result = await generate_twi_pdf(
                content=_SAMPLE_CONTENT,
                metadata=_METADATA,
                user_id="test-user",
            )
        assert result.startswith(b"%PDF")

    @pytest.mark.asyncio
    async def test_html_rendered_with_model_and_timestamp(self):
        captured: list[str] = []

        with patch(
            "app.agent.tools.pdf_generator.HTML",
            side_effect=lambda string: _mock_html(string, captured),
        ):
            await generate_twi_pdf(
                content=_SAMPLE_CONTENT,
                metadata=_METADATA,
                user_id="approver-123",
                approval_timestamp="2026-02-26T10:00:00Z",
            )

        assert captured, "HTML was never passed to WeasyPrint"
        rendered = captured[0]
        assert "mistral-large-latest" in rendered
        assert "2026-02-26 10:00 UTC" in rendered

    @pytest.mark.asyncio
    async def test_approval_box_shown_with_approver_id(self):
        captured: list[str] = []

        with patch(
            "app.agent.tools.pdf_generator.HTML",
            side_effect=lambda string: _mock_html(string, captured),
        ):
            await generate_twi_pdf(
                content=_SAMPLE_CONTENT,
                metadata=_METADATA,
                user_id="approver-001",
                approval_timestamp="2026-02-26T10:00:00Z",
            )

        rendered = captured[0]
        assert "Jóváhagyva" in rendered
        assert "approver-001" in rendered

    @pytest.mark.asyncio
    async def test_eu_ai_act_footer_present_in_template(self):
        captured: list[str] = []

        with patch(
            "app.agent.tools.pdf_generator.HTML",
            side_effect=lambda string: _mock_html(string, captured),
        ):
            await generate_twi_pdf(
                content=_SAMPLE_CONTENT,
                metadata=_METADATA,
                user_id="user-1",
            )

        rendered = captured[0]
        assert "agentize.eu" in rendered
        assert "AI által generált tartalom" in rendered
