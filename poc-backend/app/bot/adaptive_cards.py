"""Adaptive Card JSON templates for all four bot interaction points."""

from app.locale import t

_SCHEMA = "http://adaptivecards.io/schemas/adaptive-card.json"
_VERSION = "1.4"

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
                "text": t("card.review.header"),
                "weight": "bolder",
                "size": "large",
                "wrap": True,
            },
            {
                "type": "TextBlock",
                "text": t(
                    "card.review.ai_warning",
                    model=model,
                    generated_at=generated_at,
                ),
                "size": "small",
                "color": "warning",
                "wrap": True,
            },
            {"type": "TextBlock", "text": "---", "separator": True},
            {
                "type": "TextBlock",
                "text": draft[:MAX_DRAFT_DISPLAY_LENGTH],
                "wrap": True,
                "fontType": "default",
            },
            {"type": "TextBlock", "text": "---", "separator": True},
            {
                "type": "TextBlock",
                "text": t("card.review.feedback_label"),
                "size": "small",
            },
            {
                "type": "Input.Text",
                "id": "feedback",
                "isMultiline": True,
                "placeholder": t("card.review.feedback_placeholder"),
            },
        ],
        "actions": [
            {
                "type": "Action.Submit",
                "title": t("card.review.approve_btn"),
                "style": "positive",
                "data": {
                    "action": "approve_draft",
                    "draft": draft,
                    "metadata": metadata,
                },
            },
            {
                "type": "Action.Submit",
                "title": t("card.review.edit_btn"),
                "data": {
                    "action": "request_edit",
                    "draft": draft,
                    "metadata": metadata,
                },
            },
            {
                "type": "Action.Submit",
                "title": t("card.review.reject_btn"),
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
                "text": t("card.approval.header"),
                "weight": "bolder",
                "size": "large",
                "color": "attention",
                "wrap": True,
            },
            {
                "type": "TextBlock",
                "text": t("card.approval.warning"),
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
                "title": t("card.approval.confirm_btn"),
                "style": "positive",
                "data": {
                    "action": "final_approve",
                    "draft": draft,
                    "metadata": metadata,
                },
            },
            {
                "type": "Action.Submit",
                "title": t("card.approval.back_btn"),
                "data": {
                    "action": "request_edit",
                    "source": "approval",
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
                "text": t("card.result.header"),
                "weight": "bolder",
                "size": "large",
                "color": "good",
            },
            {
                "type": "FactSet",
                "facts": [
                    {
                        "title": t("card.result.title_label"),
                        "value": document_title or t("card.title_default"),
                    },
                    {
                        "title": t("card.result.format_label"),
                        "value": t("card.result.format_value"),
                    },
                    {
                        "title": t("card.result.model_label"),
                        "value": metadata.get("model", "N/A"),
                    },
                    {
                        "title": t("card.result.approved_by_label"),
                        "value": metadata.get("approved_by", "N/A"),
                    },
                ],
            },
        ],
        "actions": [
            {
                "type": "Action.OpenUrl",
                "title": t("card.result.download_btn"),
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
                "text": t("card.welcome.greeting"),
                "weight": "bolder",
                "size": "medium",
                "wrap": True,
            },
            {
                "type": "TextBlock",
                "text": t("card.welcome.description"),
                "wrap": True,
            },
            {
                "type": "TextBlock",
                "text": t("card.welcome.example"),
                "wrap": True,
                "isSubtle": True,
                "fontType": "monospace",
            },
        ],
    }
