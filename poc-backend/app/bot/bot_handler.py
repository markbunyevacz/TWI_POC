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


class AgentizeBotHandler(ActivityHandler):
    def __init__(self) -> None:
        self.graph = get_graph()
        self.conversation_store = ConversationStore()

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
        await turn_context.send_activity("⏳ Feldolgozom a kérésedet...")

        try:
            result = await run_agent(
                graph=self.graph,
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
    # Adaptive Card action → LangGraph resume
    # ------------------------------------------------------------------

    async def _handle_card_action(
        self,
        turn_context: TurnContext,
        value: dict,
        conversation_id: str,
        user_id: str,
    ) -> None:
        action = value.get("action")

        if action == "approve_draft":
            # Review #1 approved → send Final Approval card (no graph resume yet)
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
                    graph=self.graph,
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
                    graph=self.graph,
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
