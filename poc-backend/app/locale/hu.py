"""Hungarian (hu) locale strings."""

from app.locale.registry import register_locale

STRINGS: dict[str, str] = {
    # Bot handler — processing
    "bot.processing": "⏳ Feldolgozom a kérésedet...",
    "bot.error": "❌ Hiba: {message}",
    "bot.error_generic": "Hiba történt. Kérlek próbáld újra.",
    "bot.status": "Állapot: {status}",
    # Bot handler — clarification
    "bot.clarify_fallback": (
        "Kérlek pontosítsd a kérésedet. Például: "
        '"Készíts egy TWI utasítást a CNC-01 gép napi karbantartásáról."'
    ),
    # Bot handler — Telegram review
    "telegram.review.title_default": "TWI Munkautasítás",
    "telegram.review.prompt": "Kérlek válaszolj a következőkkel:",
    "telegram.review.approve": "✅ *Elfogadás* - véglegesítés",
    "telegram.review.edit": "🔄 *Módosítás* - kérek változtatást",
    "telegram.review.reject": "❌ *Elutasítás* - törlés",
    # Bot handler — Telegram approval
    "telegram.approval.title_default": "Véglegesítés",
    "telegram.approval.body": "A dokumentum elkészült! Véglegesítsem és PDF-et generáljak?",
    "telegram.approval.prompt": "Kérlek válaszolj:",
    "telegram.approval.yes": "✅ *Igen* - PDF generálás",
    "telegram.approval.no": "❌ *Nem* - elutasítás",
    # Bot handler — Telegram result
    "telegram.result.header": "✅ *Dokumentum elkészült!*",
    "telegram.result.approved_by_default": "Ismeretlen",
    # Bot handler — Telegram text commands
    "telegram.revision_prompt": "Kerlek ird le a modositasi kereseidet a dokumentumhoz:",
    "telegram.revision_processing": "⏳ Módosítom a szerkesztési kérésed alapján...",
    "telegram.approval_processing": "⏳ PDF generalas folyamatban...",
    "telegram.approval_failed": "❌ PDF generalas sikertelen: {error}",
    "telegram.revision_error": "❌ Hiba a szerkesztés során: {error}",
    "telegram.rejected": "🗑️ Elvettem a vazlatot. Uj keressel indithatsz ujat.",
    "telegram.help": (
        "Nem ertem a valaszod. Kerlek hasznald a kovetkezo parancsokat:\n\n"
        "✅ *Igen* - dokumentum elfogadasa es PDF generalas\n"
        "❌ *Nem* - dokumentum elutasitasa\n"
        "🔄 *Modositas* - modositas kérése\n\n"
        "Vagy kuldj egy uj kerest uj dokumentum generalasahoz."
    ),
    # Bot handler — card actions
    "card.approve_processing": "⏳ Véglegesítés...",
    "card.revision_processing": "⏳ Módosítom a szerkesztési kérésed alapján...",
    "card.pdf_processing": "⏳ PDF generálás folyamatban...",
    "card.pdf_failed": "❌ PDF generálás sikertelen: {error}",
    "card.revision_error": "❌ Hiba a szerkesztés során: {error}",
    "card.error": "❌ Hiba: {error}",
    "card.rejected": "🗑️ Elvettem a vázlatot. Új kéréssel indíthatsz újat.",
    "card.title_default": "TWI Munkautasítás",
    # Adaptive Cards
    "card.review.header": "📋 TWI Vázlat — Felülvizsgálat szükséges",
    "card.review.ai_warning": "⚠️ AI által generált tartalom | Modell: {model} | Generálva: {generated_at}",
    "card.review.feedback_label": "Szerkesztési megjegyzés (opcionális):",
    "card.review.feedback_placeholder": "Pl.: A 3. lépésben hiányzik a hőmérséklet beállítás...",
    "card.review.approve_btn": "✅ Jóváhagyom a vázlatot",
    "card.review.edit_btn": "✏️ Szerkesztés kérem",
    "card.review.reject_btn": "🗑️ Elvetés",
    "card.approval.header": "🔒 Véglegesítés — Kötelező Jóváhagyás",
    "card.approval.warning": (
        "⚠️ Ez a dokumentum AI által generált tartalom. "
        "Kérlek ellenőrizd a tartalmat, mielőtt véglegesíted. "
        "Véglegesítés után PDF készül és archiválásra kerül."
    ),
    "card.approval.confirm_btn": "✅ Ellenőriztem és jóváhagyom",
    "card.approval.back_btn": "↩️ Vissza a szerkesztéshez",
    "card.result.header": "✅ Dokumentum elkészült",
    "card.result.title_label": "Cím:",
    "card.result.format_label": "Formátum:",
    "card.result.format_value": "PDF",
    "card.result.model_label": "Modell:",
    "card.result.approved_by_label": "Jóváhagyta:",
    "card.result.download_btn": "📥 PDF letöltés",
    "card.welcome.greeting": "👋 Üdvözöllek! Én az agentize.eu AI asszisztens vagyok.",
    "card.welcome.description": (
        "Segíthetek TWI (Training Within Industry) munkautasítások "
        "generálásában. Írd le, milyen utasításra van szükséged!"
    ),
    "card.welcome.example": '"Készíts egy TWI utasítást a CNC-01 gép beállításáról"',
}

register_locale("hu", STRINGS)
