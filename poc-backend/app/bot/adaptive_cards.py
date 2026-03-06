"""Adaptive Card JSON templates for all four bot interaction points."""

_SCHEMA = "http://adaptivecards.io/schemas/adaptive-card.json"
_VERSION = "1.4"

# Adaptive Card payload limit for draft content (Teams limit is ~28KB, we use 2000 for safety)
MAX_DRAFT_DISPLAY_LENGTH = 2000


def create_review_card(draft: str, metadata: dict) -> dict:
    """Human-in-the-loop #1 — draft review card with approve / edit / reject actions."""
    model = metadata.get("model", "N/A")
    generated_at = metadata.get("generated_at", "N/A")

    return {
        "$schema": _SCHEMA,
        "type": "AdaptiveCard",
        "version": _VERSION,
        "body": [
            {
                "type": "TextBlock",
                "text": "📋 TWI Vázlat — Felülvizsgálat szükséges",
                "weight": "bolder",
                "size": "large",
                "wrap": True,
            },
            {
                "type": "TextBlock",
                "text": (
                    f"⚠️ AI által generált tartalom | Modell: {model} | Generálva: {generated_at}"
                ),
                "size": "small",
                "color": "warning",
                "wrap": True,
            },
            {"type": "TextBlock", "text": "---", "separator": True},
            {
                "type": "TextBlock",
                "text": draft[:MAX_DRAFT_DISPLAY_LENGTH],  # Adaptive Card payload limit
                "wrap": True,
                "fontType": "default",
            },
            {"type": "TextBlock", "text": "---", "separator": True},
            {
                "type": "TextBlock",
                "text": "Szerkesztési megjegyzés (opcionális):",
                "size": "small",
            },
            {
                "type": "Input.Text",
                "id": "feedback",
                "isMultiline": True,
                "placeholder": "Pl.: A 3. lépésben hiányzik a hőmérséklet beállítás...",
            },
        ],
        "actions": [
            {
                "type": "Action.Submit",
                "title": "✅ Jóváhagyom a vázlatot",
                "style": "positive",
                "data": {
                    "action": "approve_draft",
                    "draft": draft,
                    "metadata": metadata,
                },
            },
            {
                "type": "Action.Submit",
                "title": "✏️ Szerkesztés kérem",
                "data": {
                    "action": "request_edit",
                    "draft": draft,
                    "metadata": metadata,
                },
            },
            {
                "type": "Action.Submit",
                "title": "🗑️ Elvetés",
                "style": "destructive",
                "data": {"action": "reject"},
            },
        ],
    }


def create_approval_card(draft: str, metadata: dict) -> dict:
    """Human-in-the-loop #2 — mandatory final approval card."""
    return {
        "$schema": _SCHEMA,
        "type": "AdaptiveCard",
        "version": _VERSION,
        "body": [
            {
                "type": "TextBlock",
                "text": "🔒 Véglegesítés — Kötelező Jóváhagyás",
                "weight": "bolder",
                "size": "large",
                "color": "attention",
                "wrap": True,
            },
            {
                "type": "TextBlock",
                "text": (
                    "⚠️ Ez a dokumentum AI által generált tartalom. "
                    "Kérlek ellenőrizd a tartalmat, mielőtt véglegesíted. "
                    "Véglegesítés után PDF készül és archiválásra kerül."
                ),
                "wrap": True,
                "color": "warning",
            },
            {
                "type": "TextBlock",
                "text": draft[:MAX_DRAFT_DISPLAY_LENGTH],
                "wrap": True,
            },
        ],
        "actions": [
            {
                "type": "Action.Submit",
                "title": "✅ Ellenőriztem és jóváhagyom",
                "style": "positive",
                "data": {
                    "action": "final_approve",
                    "draft": draft,
                    "metadata": metadata,
                },
            },
            {
                "type": "Action.Submit",
                "title": "↩️ Vissza a szerkesztéshez",
                "data": {
                    "action": "request_edit",
                    "draft": draft,
                    "metadata": metadata,
                },
            },
        ],
    }


def create_result_card(pdf_url: str, document_title: str, metadata: dict) -> dict:
    """Result card with PDF download link (24-hour SAS URL)."""
    return {
        "$schema": _SCHEMA,
        "type": "AdaptiveCard",
        "version": _VERSION,
        "body": [
            {
                "type": "TextBlock",
                "text": "✅ Dokumentum elkészült",
                "weight": "bolder",
                "size": "large",
                "color": "good",
            },
            {
                "type": "FactSet",
                "facts": [
                    {"title": "Cím:", "value": document_title or "TWI Munkautasítás"},
                    {"title": "Formátum:", "value": "PDF"},
                    {"title": "Modell:", "value": metadata.get("model", "N/A")},
                    {"title": "Jóváhagyta:", "value": metadata.get("approved_by", "N/A")},
                ],
            },
        ],
        "actions": [
            {
                "type": "Action.OpenUrl",
                "title": "📥 PDF letöltés",
                "url": pdf_url,
            },
        ],
    }


def create_welcome_card() -> dict:
    """Welcome card shown when a new member joins the conversation."""
    return {
        "$schema": _SCHEMA,
        "type": "AdaptiveCard",
        "version": _VERSION,
        "body": [
            {
                "type": "TextBlock",
                "text": "👋 Üdvözöllek! Én az agentize.eu AI asszisztens vagyok.",
                "weight": "bolder",
                "size": "medium",
                "wrap": True,
            },
            {
                "type": "TextBlock",
                "text": (
                    "Segíthetek TWI (Training Within Industry) munkautasítások "
                    "generálásában. Írd le, milyen utasításra van szükséged!"
                ),
                "wrap": True,
            },
            {
                "type": "TextBlock",
                "text": (
                    "Példa: \"Készíts egy TWI utasítást a CNC-01 gép beállításáról\""
                ),
                "wrap": True,
                "isSubtle": True,
                "fontType": "monospace",
            },
        ],
    }
