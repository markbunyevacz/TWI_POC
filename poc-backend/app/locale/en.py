"""English (en) locale strings."""

from app.locale.registry import register_locale

STRINGS: dict[str, str] = {
    # Bot handler — processing
    "bot.processing": "⏳ Processing your request...",
    "bot.error": "❌ Error: {message}",
    "bot.error_generic": "An error occurred. Please try again.",
    "bot.status": "Status: {status}",
    # Bot handler — clarification
    "bot.clarify_fallback": (
        "Please clarify your request. For example: "
        '"Create a TWI instruction for the daily maintenance of the CNC-01 machine."'
    ),
    # Bot handler — Telegram review (plain text, no Markdown — avoids MarkdownV2 parse errors)
    "telegram.review.title_default": "TWI Work Instruction",
    "telegram.review.prompt": "Please reply with one of the following:",
    "telegram.review.approve": "✅ Approve - finalize",
    "telegram.review.edit": "🔄 Edit - request changes",
    "telegram.review.reject": "❌ Reject - discard",
    # Bot handler — Telegram approval (plain text)
    "telegram.approval.title_default": "Final Approval",
    "telegram.approval.body": "The document is ready! Shall I finalize and generate the PDF?",
    "telegram.approval.prompt": "Please reply:",
    "telegram.approval.yes": "✅ Yes - Generate PDF",
    "telegram.approval.no": "❌ No - Reject",
    # Bot handler — Telegram result (plain text)
    "telegram.result.header": "✅ Document ready!",
    "telegram.result.approved_by_default": "Unknown",
    # Bot handler — Telegram text commands
    "telegram.revision_prompt": "Please describe the changes you'd like to make to the document:",
    "telegram.revision_processing": "⏳ Applying your edits...",
    "telegram.approval_processing": "⏳ Generating PDF...",
    "telegram.approval_failed": "❌ PDF generation failed: {error}",
    "telegram.revision_error": "❌ Error during revision: {error}",
    "telegram.rejected": "🗑️ Draft discarded. Send a new request to start over.",
    "telegram.help": (
        "I didn't understand your response. Please use one of these commands:\n\n"
        "✅ Yes - approve document and generate PDF\n"
        "❌ No - reject document\n"
        "🔄 Edit - request changes\n\n"
        "Or send a new request to generate a new document."
    ),
    # Bot handler — card actions
    "card.approve_processing": "⏳ Finalizing...",
    "card.revision_processing": "⏳ Applying your edits...",
    "card.pdf_processing": "⏳ Generating PDF...",
    "card.pdf_failed": "❌ PDF generation failed: {error}",
    "card.revision_error": "❌ Error during revision: {error}",
    "card.error": "❌ Error: {error}",
    "card.rejected": "🗑️ Draft discarded. Send a new request to start over.",
    "card.title_default": "TWI Work Instruction",
    # Adaptive Cards
    "card.review.header": "📋 TWI Draft — Review Required",
    "card.review.ai_warning": "⚠️ AI-generated content | Model: {model} | Generated: {generated_at}",
    "card.review.feedback_label": "Edit notes (optional):",
    "card.review.feedback_placeholder": "E.g.: Step 3 is missing the temperature setting...",
    "card.review.approve_btn": "✅ Approve draft",
    "card.review.edit_btn": "✏️ Request edit",
    "card.review.reject_btn": "🗑️ Discard",
    "card.approval.header": "🔒 Final Approval — Mandatory",
    "card.approval.warning": (
        "⚠️ This document contains AI-generated content. "
        "Please review the content before finalizing. "
        "After approval, a PDF will be generated and archived."
    ),
    "card.approval.confirm_btn": "✅ I have reviewed and approve",
    "card.approval.back_btn": "↩️ Back to editing",
    "card.result.header": "✅ Document ready",
    "card.result.title_label": "Title:",
    "card.result.format_label": "Format:",
    "card.result.format_value": "PDF",
    "card.result.model_label": "Model:",
    "card.result.approved_by_label": "Approved by:",
    "card.result.download_btn": "📥 Download PDF",
    "card.welcome.greeting": "👋 Welcome! I'm the agentize.eu AI assistant.",
    "card.welcome.description": (
        "I can help generate TWI (Training Within Industry) work instructions. "
        "Describe what instruction you need!"
    ),
    "card.welcome.example": '"Create a TWI instruction for CNC-01 machine setup"',
}

register_locale("en", STRINGS)
