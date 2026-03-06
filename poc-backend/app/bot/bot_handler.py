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
        # Guard: if the graph already has a paused thread for this conversation,
        # warn the user instead of orphaning the existing run.
        try:
            existing = await self.graph.aget_state(
                {"configurable": {"thread_id": conversation_id}}
            )
            if existing and existing.next:
                logger.info(
                    "Graph already paused at %s for conversation=%s — prompting user.",
                    existing.next,
                    conversation_id,
                )
                await self._send_message(
                    turn_context,
                    "⚠️ Már van egy folyamatban lévő kérésed. "
                    "Kérlek használd a kártyán lévő gombokat a folytatáshoz, "
                    "vagy utasítsd el a jelenlegi vázlatot, mielőtt újat kezdesz.",
                    channel_id,
                )
                return
        except Exception:
            # If state lookup fails (e.g. no checkpointer), proceed normally.
            pass

        await self._send_message(turn_context, "⏳ Feldolgozom a kérésedet...", channel_id)

        try:
            result = await run_agent(
                graph=self.graph,
                message=text,
                user_id=user_id,
                conversation_id=conversation_id,
                channel=channel_id,
            )
        except (ValueError, KeyError, RuntimeError) as exc:
            logger.error("Agent error: %s", exc, exc_info=True)
            await self._send_message(
                turn_context,
                "❌ Hiba történt a feldolgozás során. Kérlek próbáld újra.",
                channel_id,
            )
            return
        except Exception as exc:  # noqa: BLE001
            logger.error("Unexpected agent error: %s", exc, exc_info=True)
            await self._send_message(
                turn_context,
                "❌ Váratlan hiba történt. Kérlek próbáld újra később.",
                channel_id,
            )
            return

        status = result.get("status", "")

        if status == "review_needed":
            card = create_review_card(
                draft=result.get("draft", ""),
                metadata=result.get("draft_metadata", {}),
            )
            await self._send_card(turn_context, card, channel_id)

        elif status == "clarification_needed":
            clarify_msg = (
                "Kérlek pontosítsd a kérésedet. Például: "
                '"Készíts egy TWI utasítást a CNC-01 gép napi karbantartásáról."'
            )
            await self._send_message(turn_context, clarify_msg, channel_id)

        elif status == "error":
            await self._send_message(
                turn_context,
                "❌ Hiba történt a feldolgozás során. Kérlek próbáld újra.",
                channel_id,
            )

        else:
            await self._send_message(
                turn_context, f"Állapot: {status}", channel_id
            )

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

        channel_id = turn_context.activity.channel_id

        if action == "approve_draft":
            # Review #1 approved → send Final Approval card (no graph resume yet)
            card = create_approval_card(
                draft=value.get("draft", ""),
                metadata=value.get("metadata", {}),
            )
            await self._send_card(turn_context, card, channel_id)

        elif action == "request_edit":
            # Revision requested → resume graph with revision feedback
            feedback = value.get("feedback", "")
            await self._send_message(
                turn_context,
                "⏳ Módosítom a szerkesztési kérésed alapján...",
                channel_id,
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
            except (ValueError, KeyError, RuntimeError) as exc:
                logger.error("Agent revision error: %s", exc, exc_info=True)
                await self._send_message(
                    turn_context,
                    "❌ Hiba a szerkesztés során. Kérlek próbáld újra.",
                    channel_id,
                )
                return
            except Exception as exc:  # noqa: BLE001
                logger.error("Unexpected agent revision error: %s", exc, exc_info=True)
                await self._send_message(
                    turn_context,
                    "❌ Váratlan hiba történt. Kérlek próbáld újra később.",
                    channel_id,
                )
                return

            card = create_review_card(
                draft=result.get("draft", ""),
                metadata=result.get("draft_metadata", {}),
            )
            await self._send_card(turn_context, card, channel_id)

        elif action == "final_approve":
            # Final approval → resume graph → PDF generation
            await self._send_message(
                turn_context, "⏳ PDF generálás folyamatban...", channel_id
            )
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
            except (ValueError, KeyError, RuntimeError) as exc:
                logger.error("Agent output error: %s", exc, exc_info=True)
                await self._send_message(
                    turn_context,
                    "❌ PDF generálás sikertelen. Kérlek próbáld újra.",
                    channel_id,
                )
                return
            except Exception as exc:  # noqa: BLE001
                logger.error("Unexpected agent output error: %s", exc, exc_info=True)
                await self._send_message(
                    turn_context,
                    "❌ Váratlan hiba történt. Kérlek próbáld újra később.",
                    channel_id,
                )
                return

            # Enrich metadata with approver info for the result card
            metadata = result.get("draft_metadata", {})
            metadata["approved_by"] = user_id

            card = create_result_card(
                pdf_url=result.get("pdf_url", "#"),
                document_title=result.get("title", "TWI Munkautasítás"),
                metadata=metadata,
            )
            await self._send_card(turn_context, card, channel_id)

        elif action == "reject":
            await self._send_message(
                turn_context,
                "🗑️ Elvettem a vázlatot. Új kéréssel indíthatsz újat.",
                channel_id,
            )

        else:
            logger.warning("Unknown card action: %s", action)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _is_telegram(channel_id: str) -> bool:
        """Check if the current channel is Telegram."""
        return channel_id == "telegram"

    @staticmethod
    async def _send_message(
        turn_context: TurnContext, text: str, channel_id: str = ""
    ) -> None:
        """Send a plain text message.  Works on all channels."""
        await turn_context.send_activity(text)

    @staticmethod
    async def _send_card(
        turn_context: TurnContext, card: dict, channel_id: str = ""
    ) -> None:
        """Send an Adaptive Card, with a Telegram plain-text fallback.

        Telegram does not support Adaptive Cards, so we extract the
        text blocks and send them as a Markdown-formatted message.
        """
        if channel_id == "telegram":
            # Telegram fallback: extract readable text from the card body
            lines: list[str] = []
            for block in card.get("body", []):
                text = block.get("text", "")
                if text and text != "---":
                    lines.append(text)
                # FactSet support (used in result card)
                for fact in block.get("facts", []):
                    lines.append(f"{fact.get('title', '')} {fact.get('value', '')}")
            # Append action labels / URLs
            for action in card.get("actions", []):
                title = action.get("title", "")
                url = action.get("url")
                if url:
                    lines.append(f"{title}: {url}")
                elif title:
                    lines.append(f"[{title}]")
            await turn_context.send_activity("\n".join(lines))
        else:
            await turn_context.send_activity(
                Activity(
                    type=ActivityTypes.message,
                    attachments=[CardFactory.adaptive_card(card)],
                )
            )
