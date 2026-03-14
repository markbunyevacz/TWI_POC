import logging
from datetime import datetime, timezone

from botbuilder.core import ActivityHandler, TurnContext, CardFactory
from botbuilder.schema import Activity, ActivityTypes

from app.agent.graph import run_agent
from app.bot.adaptive_cards import (
    create_review_card,
    create_approval_card,
    create_result_card,
    create_welcome_card,
)
from app.locale import t
from app.services.cosmos_db import ConversationStore, PendingStateStore

logger = logging.getLogger(__name__)


def _is_telegram_channel(channel_id: str) -> bool:
    """Check if the channel is Telegram."""
    return bool(channel_id and channel_id.lower() == "telegram")


def _format_telegram_review(draft: str, metadata: dict) -> str:
    """Format draft content for Telegram (no Adaptive Cards support)."""
    title = metadata.get("title", t("telegram.review.title_default"))
    model = metadata.get("model", "N/A")
    generated_at = metadata.get("generated_at", "N/A")

    text = f"📋 *{title}*\n\n"
    text += f"_Model: {model} | Generated: {generated_at}_\n\n"
    text += f"```\n{draft[:500]}"
    if len(draft) > 500:
        text += "... (truncated)"
    text += "\n```\n\n"
    text += t("telegram.review.prompt") + "\n"
    text += t("telegram.review.approve") + "\n"
    text += t("telegram.review.edit") + "\n"
    text += t("telegram.review.reject")
    return text


def _format_telegram_approval(draft: str, metadata: dict) -> str:
    """Format final approval request for Telegram."""
    title = metadata.get("title", t("telegram.approval.title_default"))

    text = f"📄 *{title}*\n\n"
    text += t("telegram.approval.body") + "\n\n"
    text += t("telegram.approval.prompt") + "\n"
    text += t("telegram.approval.yes") + "\n"
    text += t("telegram.approval.no")
    return text


def _format_telegram_result(pdf_url: str, document_title: str, metadata: dict) -> str:
    """Format result message for Telegram."""
    approved_by = metadata.get("approved_by", t("telegram.result.approved_by_default"))
    text = t("telegram.result.header") + "\n\n"
    text += f"📄 *{document_title}*\n\n"
    text += f"👤 {t('card.result.approved_by_label')} {approved_by}\n"
    text += f"📥 {t('card.result.download_btn')}: {pdf_url}"
    return text


class AgentizeBotHandler(ActivityHandler):
    def __init__(self) -> None:
        self.graph = None
        self.conversation_store = ConversationStore()
        self._pending_state = PendingStateStore()

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
        value = turn_context.activity.value

        logger.info(
            "Message from user=%s channel=%s text=%.50s",
            user_id,
            channel_id,
            text,
        )

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
            await self._handle_telegram_text(
                turn_context, text, conversation_id, user_id
            )
        else:
            await self._handle_text_message(
                turn_context, text, conversation_id, user_id, channel_id
            )

    async def on_members_added_activity(
        self, members_added, turn_context: TurnContext
    ) -> None:
        """Send a welcome card when the bot is added to a conversation."""
        for member in members_added:
            if member.id != turn_context.activity.recipient.id:
                card = create_welcome_card()
                await self._send_card(turn_context, card)

    # ------------------------------------------------------------------
    # Text message -> LangGraph
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

        await turn_context.send_activity(t("bot.processing"))

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
            await turn_context.send_activity(t("bot.error", message=exc))
            return

        status = result.get("status", "")

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
            clarify_msg = result.get("draft") or t("bot.clarify_fallback")
            await turn_context.send_activity(clarify_msg)

        elif status == "error":
            msg = result.get("message", t("bot.error_generic"))
            await turn_context.send_activity(t("bot.error", message=msg))

        else:
            await turn_context.send_activity(t("bot.status", status=status))

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
            clarify_msg = result.get("draft") or t("bot.clarify_fallback")
            await turn_context.send_activity(clarify_msg)

        elif status == "error":
            msg = result.get("message", t("bot.error_generic"))
            await turn_context.send_activity(t("bot.error", message=msg))

        else:
            await turn_context.send_activity(t("bot.status", status=status))

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

        if await self._pending_state.pop_flag(conversation_id, "pending_revision"):
            await turn_context.send_activity(t("telegram.revision_processing"))
            try:
                result = await run_agent(
                    graph=await self._get_graph(),
                    message=text,
                    user_id=user_id,
                    conversation_id=conversation_id,
                    resume_from="revision",
                    context={"feedback": text},
                )
            except Exception as exc:
                logger.error("Telegram revision error: %s", exc, exc_info=True)
                await turn_context.send_activity(
                    t("telegram.revision_error", error=exc)
                )
                return

            reply = _format_telegram_review(
                result.get("draft", ""),
                result.get("draft_metadata", {}),
            )
            await turn_context.send_activity(reply)
            return

        if text_lower in [
            "igen",
            "yes",
            "y",
            "i",
            "elfogadas",
            "elfogad",
            "approve",
            "approved",
        ]:
            await turn_context.send_activity(t("telegram.approval_processing"))
            timestamp = datetime.now(timezone.utc).isoformat()

            try:
                result = await run_agent(
                    graph=await self._get_graph(),
                    message="",
                    user_id=user_id,
                    conversation_id=conversation_id,
                    resume_from="output",
                    context={"timestamp": timestamp},
                    as_node="approve",
                )
            except Exception as exc:
                logger.error("Agent output error: %s", exc, exc_info=True)
                await turn_context.send_activity(
                    t("telegram.approval_failed", error=exc)
                )
                return

            metadata = result.get("draft_metadata", {})
            metadata["approved_by"] = user_id

            text = _format_telegram_result(
                result.get("pdf_url", "#"),
                result.get("title", t("card.title_default")),
                metadata,
            )
            await turn_context.send_activity(text)

        elif text_lower in [
            "nem",
            "no",
            "n",
            "elutasitas",
            "elutasit",
            "reject",
            "rejected",
        ]:
            await turn_context.send_activity(t("telegram.rejected"))
            try:
                await run_agent(
                    graph=await self._get_graph(),
                    message="",
                    user_id=user_id,
                    conversation_id=conversation_id,
                    resume_from="rejection",
                    as_node="review",
                )
            except Exception as exc:
                logger.error("Rejection audit failed: %s", exc, exc_info=True)

        elif text_lower in ["modositas", "change", "modify", "revise"]:
            await self._pending_state.set_flag(conversation_id, "pending_revision")
            await turn_context.send_activity(t("telegram.revision_prompt"))

        elif text_lower.startswith(
            ("modositas:", "módosítás:", "change:", "modify:", "revise:")
        ):
            feedback = text.split(":", 1)[1].strip()
            if not feedback:
                await turn_context.send_activity(t("telegram.revision_prompt"))
                return
            await turn_context.send_activity(t("telegram.revision_processing"))
            try:
                result = await run_agent(
                    graph=await self._get_graph(),
                    message=feedback,
                    user_id=user_id,
                    conversation_id=conversation_id,
                    resume_from="revision",
                    context={"feedback": feedback},
                )
            except Exception as exc:
                logger.error("Telegram revision error: %s", exc, exc_info=True)
                await turn_context.send_activity(
                    t("telegram.revision_error", error=exc)
                )
                return
            reply = _format_telegram_review(
                result.get("draft", ""),
                result.get("draft_metadata", {}),
            )
            await turn_context.send_activity(reply)

        else:
            await self._handle_text_message(
                turn_context, text, conversation_id, user_id, "telegram"
            )

    # ------------------------------------------------------------------
    # Adaptive Card action -> LangGraph resume
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
            if is_telegram:
                await turn_context.send_activity(t("card.approve_processing"))
                timestamp = datetime.now(timezone.utc).isoformat()
                try:
                    result = await run_agent(
                        graph=await self._get_graph(),
                        message="",
                        user_id=user_id,
                        conversation_id=conversation_id,
                        resume_from="output",
                        context={"timestamp": timestamp},
                        as_node="approve",
                    )
                except Exception as exc:
                    logger.error("Agent output error: %s", exc, exc_info=True)
                    await turn_context.send_activity(t("card.error", error=exc))
                    return

                metadata = result.get("draft_metadata", {})
                metadata["approved_by"] = user_id

                text = _format_telegram_result(
                    result.get("pdf_url", "#"),
                    result.get("title", t("card.title_default")),
                    metadata,
                )
                await turn_context.send_activity(text)
            else:
                card = create_approval_card(
                    draft=value.get("draft", ""),
                    metadata=value.get("metadata", {}),
                )
                await self._send_card(turn_context, card)

        elif action == "request_edit":
            feedback = value.get("feedback", "")
            resume_as_node = "review"

            await turn_context.send_activity(t("card.revision_processing"))

            try:
                result = await run_agent(
                    graph=await self._get_graph(),
                    message=feedback,
                    user_id=user_id,
                    conversation_id=conversation_id,
                    resume_from="revision",
                    context={"feedback": feedback},
                    as_node=resume_as_node,
                )
            except Exception as exc:  # noqa: BLE001
                logger.error("Agent revision error: %s", exc, exc_info=True)
                await turn_context.send_activity(t("card.revision_error", error=exc))
                return

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
            await turn_context.send_activity(t("card.pdf_processing"))
            timestamp = datetime.now(timezone.utc).isoformat()

            try:
                result = await run_agent(
                    graph=await self._get_graph(),
                    message="",
                    user_id=user_id,
                    conversation_id=conversation_id,
                    resume_from="output",
                    context={"timestamp": timestamp},
                    as_node="approve",
                )
            except Exception as exc:  # noqa: BLE001
                logger.error("Agent output error: %s", exc, exc_info=True)
                await turn_context.send_activity(t("card.pdf_failed", error=exc))
                return

            metadata = result.get("draft_metadata", {})
            metadata["approved_by"] = user_id

            if is_telegram:
                text = _format_telegram_result(
                    result.get("pdf_url", "#"),
                    result.get("title", t("card.title_default")),
                    metadata,
                )
                await turn_context.send_activity(text)
            else:
                card = create_result_card(
                    pdf_url=result.get("pdf_url", "#"),
                    document_title=result.get("title", t("card.title_default")),
                    metadata=metadata,
                )
                await self._send_card(turn_context, card)

        elif action == "reject":
            await turn_context.send_activity(t("card.rejected"))
            try:
                await run_agent(
                    graph=await self._get_graph(),
                    message="",
                    user_id=user_id,
                    conversation_id=conversation_id,
                    resume_from="rejection",
                    as_node="review",
                )
            except Exception as exc:
                logger.error("Rejection audit failed: %s", exc, exc_info=True)

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
