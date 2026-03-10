import logging
from datetime import datetime, timezone

from botbuilder.core import ActivityHandler, TurnContext, CardFactory
from botbuilder.schema import Activity, ActivityTypes

from app.agent.graph import get_graph, run_agent
from app.bot.adaptive_cards import (
    create_review_card,
    create_approval_card,
    create_result_card,
    create_welcome_card,
)
from app.services.cosmos_db import ConversationStore

logger = logging.getLogger(__name__)


def _is_telegram_channel(channel_id: str) -> bool:
    """Check if the channel is Telegram."""
    return channel_id and channel_id.lower() == "telegram"


def _format_telegram_review(draft: str, metadata: dict) -> str:
    """Format draft content for Telegram (no Adaptive Cards support)."""
    title = metadata.get("title", "TWI Munkautasítás")
    model = metadata.get("model", "N/A")
    generated_at = metadata.get("generated_at", "N/A")
    
    text = f"📋 *{title}*\n\n"
    text += f"_Model: {model} | Generated: {generated_at}_\n\n"
    text += f"```\n{draft[:500]}"
    if len(draft) > 500:
        text += "... (truncated)"
    text += "\n```\n\n"
    text += "Kérlek válaszolj a következőkkel:\n"
    text += "✅ *Elfogadás* - véglegesítés\n"
    text += "🔄 *Módosítás* - kérek változtatást\n"
    text += "❌ *Elutasítás* - törlés"
    return text


def _format_telegram_approval(draft: str, metadata: dict) -> str:
    """Format final approval request for Telegram."""
    title = metadata.get("title", "Véglegesítés")
    
    text = f"📄 *{title}*\n\n"
    text += "A dokumentum elkészült! Véglegesítsem és PDF-et generáljak?\n\n"
    text += "Kérlek válaszolj:\n"
    text += "✅ *Igen* - PDF generálás\n"
    text += "❌ *Nem* - elutasítás"
    return text


def _format_telegram_result(pdf_url: str, document_title: str, metadata: dict) -> str:
    """Format result message for Telegram."""
    approved_by = metadata.get("approved_by", "Ismeretlen")
    text = f"✅ *Dokumentum elkészült!*\n\n"
    text += f"📄 *{document_title}*\n\n"
    text += f"👤 Jóváhagyta: {approved_by}\n"
    text += f"📥 Letöltés: {pdf_url}"
    return text


class AgentizeBotHandler(ActivityHandler):
    def __init__(self) -> None:
        # Note: graph is initialized lazily since get_graph is now async
        self.graph = None
        self.conversation_store = ConversationStore()
    
    async def _get_graph(self):
        """Lazy initialization of the graph."""
        if self.graph is None:
            from app.agent.graph import get_graph
            self.graph = await get_graph()
        return self.graph

    # ------------------------------------------------------------------
    # Activity routing
    # ------------------------------------------------------------------

    async def on_message_activity(self, turn_context: TurnContext) -> None:
        user_id = turn_context.activity.from_property.id
        conversation_id = turn_context.activity.conversation.id
        channel_id = turn_context.activity.channel_id
        text: str = turn_context.activity.text or ""
        value = turn_context.activity.value  # set when an Adaptive Card is submitted

        logger.info(
            "Message from user=%s channel=%s text=%.50s",
            user_id,
            channel_id,
            text,
        )

        # Track the conversation in Cosmos DB
        await self.conversation_store.get_or_create(
            conversation_id=conversation_id,
            user_id=user_id,
            channel=channel_id,
        )

        if value:
            await self._handle_card_action(
                turn_context, value, conversation_id, user_id
            )
        elif _is_telegram_channel(channel_id):
            # Handle Telegram text responses (Igen/Nem for approvals)
            await self._handle_telegram_text(
                turn_context, text, conversation_id, user_id
            )
        else:
            await self._handle_text_message(
                turn_context, text, conversation_id, user_id, channel_id
            )

    async def on_members_added_activity(self, members_added, turn_context: TurnContext) -> None:
        """Send a welcome card when the bot is added to a conversation."""
        for member in members_added:
            if member.id != turn_context.activity.recipient.id:
                card = create_welcome_card()
                await self._send_card(turn_context, card)

    # ------------------------------------------------------------------
    # Text message → LangGraph
    # ------------------------------------------------------------------

    async def _handle_text_message(
        self,
        turn_context: TurnContext,
        text: str,
        conversation_id: str,
        user_id: str,
        channel_id: str,
    ) -> None:
        is_telegram = _is_telegram_channel(channel_id)
        
        await turn_context.send_activity("⏳ Feldolgozom a kérésedet...")

        try:
            result = await run_agent(
                graph=await self._get_graph(),
                message=text,
                user_id=user_id,
                conversation_id=conversation_id,
                channel=channel_id,
            )
        except Exception as exc:  # noqa: BLE001
            logger.error("Agent error: %s", exc, exc_info=True)
            await turn_context.send_activity(f"❌ Hiba: {exc}")
            return

        status = result.get("status", "")
        
        # Handle Telegram channel - no Adaptive Cards support
        if is_telegram:
            await self._handle_telegram_response(turn_context, result, status)
            return

        if status == "review_needed":
            card = create_review_card(
                draft=result.get("draft", ""),
                metadata=result.get("draft_metadata", {}),
            )
            await self._send_card(turn_context, card)

        elif status == "clarification_needed":
            clarify_msg = (
                "Kérlek pontosítsd a kérésedet. Például: "
                '"Készíts egy TWI utasítást a CNC-01 gép napi karbantartásáról."'
            )
            await turn_context.send_activity(clarify_msg)

        elif status == "error":
            msg = result.get("message", "Ismeretlen hiba")
            await turn_context.send_activity(f"❌ Hiba: {msg}")

        else:
            await turn_context.send_activity(f"Állapot: {status}")
    
    # ------------------------------------------------------------------
    # Telegram-specific response handlers (no Adaptive Cards)
    # ------------------------------------------------------------------
    
    async def _handle_telegram_response(
        self,
        turn_context: TurnContext,
        result: dict,
        status: str,
    ) -> None:
        """Handle Telegram responses when Adaptive Cards are not supported."""
        if status == "review_needed":
            text = _format_telegram_review(
                result.get("draft", ""),
                result.get("draft_metadata", {}),
            )
            await turn_context.send_activity(text)
            
        elif status == "clarification_needed":
            clarify_msg = (
                "Kérlek pontosítsd a kérésedet. Például: "
                '"Készíts egy TWI utasítást a CNC-01 gép napi karbantartásáról."'
            )
            await turn_context.send_activity(clarify_msg)
            
        elif status == "error":
            msg = result.get("message", "Ismeretlen hiba")
            await turn_context.send_activity(f"❌ Hiba: {msg}")
            
        else:
            await turn_context.send_activity(f"Állapot: {status}")

    # ------------------------------------------------------------------
    # Telegram text response handler (Igen/Nem)
    # ------------------------------------------------------------------
    
    async def _handle_telegram_text(
        self,
        turn_context: TurnContext,
        text: str,
        conversation_id: str,
        user_id: str,
    ) -> None:
        """Handle text responses from Telegram users for approvals."""
        text_lower = text.lower().strip()
        
        # Check for approval responses
        if text_lower in ["igen", "yes", "y", "i", "elfogadas", "elfogad", "approve", "approved"]:
            # Final approval → resume graph → PDF generation
            await turn_context.send_activity("⏳ PDF generalas folyamatban...")
            timestamp = datetime.now(timezone.utc).isoformat()

            try:
                result = await run_agent(
                    graph=await self._get_graph(),
                    message="",
                    user_id=user_id,
                    conversation_id=conversation_id,
                    resume_from="output",
                    context={"timestamp": timestamp},
                )
            except Exception as exc:
                logger.error("Agent output error: %s", exc, exc_info=True)
                await turn_context.send_activity(f"❌ PDF generalas sikertelen: {exc}")
                return

            metadata = result.get("draft_metadata", {})
            metadata["approved_by"] = user_id

            text = _format_telegram_result(
                result.get("pdf_url", "#"),
                result.get("title", "TWI Munkautasitas"),
                metadata,
            )
            await turn_context.send_activity(text)
            
        # Check for rejection responses
        elif text_lower in ["nem", "no", "n", "elutasitas", "elutasit", "reject", "rejected"]:
            await turn_context.send_activity(
                "🗑️ Elvettem a vazlatot. Uj keressel indithatsz ujat."
            )
            
        # Check for revision requests
        elif text_lower in ["modositas", "change", "modify", "revise"]:
            await turn_context.send_activity(
                "Kerlek ird le a modositasi keteseidet a dokumentumhoz:"
            )
            
        else:
            # Not a recognized command - explain options
            help_text = (
                "Nem ertem a valaszod. Kerlek hasznald a kovetkezo parancsokat:\n\n"
                "✅ *Igen* - dokumentum elfogadasa es PDF generalas\n"
                "❌ *Nem* - dokumentum elutasitasa\n"
                "🔄 *Modositas* - modositas kérése\n\n"
                "Vagy kuldj egy uj kerest uj dokumentum generalasahoz."
            )
            await turn_context.send_activity(help_text)

    # ------------------------------------------------------------------
    # Adaptive Card action → LangGraph resume
    # ------------------------------------------------------------------

    async def _handle_card_action(
        self,
        turn_context: TurnContext,
        value: dict,
        conversation_id: str,
        user_id: str,
    ) -> None:
        channel_id = turn_context.activity.channel_id
        is_telegram = _is_telegram_channel(channel_id)
        action = value.get("action")

        if action == "approve_draft":
            # For Telegram, directly proceed to final approval
            if is_telegram:
                await turn_context.send_activity("⏳ Véglegesítés...")
                timestamp = datetime.now(timezone.utc).isoformat()
                try:
                    result = await run_agent(
                        graph=await self._get_graph(),
                        message="",
                        user_id=user_id,
                        conversation_id=conversation_id,
                        resume_from="output",
                        context={"timestamp": timestamp},
                    )
                except Exception as exc:
                    logger.error("Agent output error: %s", exc, exc_info=True)
                    await turn_context.send_activity(f"❌ Hiba: {exc}")
                    return
                
                metadata = result.get("draft_metadata", {})
                metadata["approved_by"] = user_id
                
                text = _format_telegram_result(
                    result.get("pdf_url", "#"),
                    result.get("title", "TWI Munkautasítás"),
                    metadata,
                )
                await turn_context.send_activity(text)
            else:
                # Teams - send Final Approval card
                card = create_approval_card(
                    draft=value.get("draft", ""),
                    metadata=value.get("metadata", {}),
                )
                await self._send_card(turn_context, card)

        elif action == "request_edit":
            # Revision requested → resume graph with revision feedback
            feedback = value.get("feedback", "")
            await turn_context.send_activity(
                "⏳ Módosítom a szerkesztési kérésed alapján..."
            )

            try:
                result = await run_agent(
                    graph=await self._get_graph(),
                    message=feedback,
                    user_id=user_id,
                    conversation_id=conversation_id,
                    resume_from="revision",
                    context={"feedback": feedback},
                )
            except Exception as exc:  # noqa: BLE001
                logger.error("Agent revision error: %s", exc, exc_info=True)
                await turn_context.send_activity(f"❌ Hiba a szerkesztés során: {exc}")
                return

            # Send appropriate response based on channel
            if is_telegram:
                text = _format_telegram_review(
                    result.get("draft", ""),
                    result.get("draft_metadata", {}),
                )
                await turn_context.send_activity(text)
            else:
                card = create_review_card(
                    draft=result.get("draft", ""),
                    metadata=result.get("draft_metadata", {}),
                )
                await self._send_card(turn_context, card)

        elif action == "final_approve":
            # Final approval → resume graph → PDF generation
            await turn_context.send_activity("⏳ PDF generálás folyamatban...")
            timestamp = datetime.now(timezone.utc).isoformat()

            try:
                result = await run_agent(
                    graph=await self._get_graph(),
                    message="",
                    user_id=user_id,
                    conversation_id=conversation_id,
                    resume_from="output",
                    context={"timestamp": timestamp},
                )
            except Exception as exc:  # noqa: BLE001
                logger.error("Agent output error: %s", exc, exc_info=True)
                await turn_context.send_activity(f"❌ PDF generálás sikertelen: {exc}")
                return

            # Enrich metadata with approver info for the result card
            metadata = result.get("draft_metadata", {})
            metadata["approved_by"] = user_id

            if is_telegram:
                text = _format_telegram_result(
                    result.get("pdf_url", "#"),
                    result.get("title", "TWI Munkautasítás"),
                    metadata,
                )
                await turn_context.send_activity(text)
            else:
                card = create_result_card(
                    pdf_url=result.get("pdf_url", "#"),
                    document_title=result.get("title", "TWI Munkautasítás"),
                    metadata=metadata,
                )
                await self._send_card(turn_context, card)

        elif action == "reject":
            await turn_context.send_activity(
                "🗑️ Elvettem a vázlatot. Új kéréssel indíthatsz újat."
            )

        else:
            logger.warning("Unknown card action: %s", action)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    async def _send_card(turn_context: TurnContext, card: dict) -> None:
        await turn_context.send_activity(
            Activity(
                type=ActivityTypes.message,
                attachments=[CardFactory.adaptive_card(card)],
            )
        )
