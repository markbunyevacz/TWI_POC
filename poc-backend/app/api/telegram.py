"""Telegram webhook endpoint and registration helper.

This module provides:
- ``POST /api/telegram/webhook`` — receives Telegram updates and routes
  them through the Bot Framework adapter as if they came from Azure Bot
  Service's Telegram channel.
- ``register_webhook()`` — call during startup to register the webhook
  URL with the Telegram Bot API (requires ``TELEGRAM_BOT_TOKEN`` and a
  publicly reachable ``BASE_URL``).
"""

import logging

import httpx
from fastapi import APIRouter, Request, Response

from app.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/telegram", tags=["telegram"])


async def register_webhook(base_url: str) -> bool:
    """Register the webhook URL with Telegram Bot API.

    Args:
        base_url: The publicly reachable base URL of this service
                  (e.g. ``https://myapp.azurecontainerapps.io``).

    Returns:
        ``True`` if registration succeeded, ``False`` otherwise.
    """
    if not settings.telegram_bot_token:
        logger.info("TELEGRAM_BOT_TOKEN not set — skipping webhook registration.")
        return False

    webhook_url = f"{base_url.rstrip('/')}/api/telegram/webhook"
    api_url = (
        f"https://api.telegram.org/bot{settings.telegram_bot_token}/setWebhook"
    )

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(api_url, json={"url": webhook_url})
            data = resp.json()
            if data.get("ok"):
                logger.info("Telegram webhook registered: %s", webhook_url)
                return True
            logger.warning("Telegram webhook registration failed: %s", data)
            return False
    except Exception as exc:
        logger.error("Telegram webhook registration error: %s", exc)
        return False


@router.post("/webhook")
async def telegram_webhook(request: Request) -> Response:
    """Receive Telegram updates and convert them to Bot Framework activities.

    This is a lightweight bridge: it extracts the message text and user
    info from the Telegram update JSON and forwards it to the bot handler
    through the Bot Framework adapter.

    .. note::
       For a production deployment, this should validate the update using
       a webhook secret token (``X-Telegram-Bot-Api-Secret-Token`` header).
    """
    if not settings.telegram_bot_token:
        return Response(status_code=503, content="Telegram not configured")

    try:
        update = await request.json()
    except Exception:
        return Response(status_code=400, content="Invalid JSON")

    message = update.get("message") or update.get("edited_message")
    if not message:
        # Non-message updates (e.g. callback_query) are not yet handled
        return Response(status_code=200)

    text = message.get("text", "")
    chat_id = str(message["chat"]["id"])
    user = message.get("from", {})
    user_id = str(user.get("id", "unknown"))

    logger.info(
        "Telegram update: chat_id=%s user_id=%s text=%.50s",
        chat_id,
        user_id,
        text,
    )

    # Import here to avoid circular imports at module level
    from app.main import adapter, bot
    from botbuilder.schema import Activity, ActivityTypes, ChannelAccount

    activity = Activity(
        type=ActivityTypes.message,
        text=text,
        channel_id="telegram",
        from_property=ChannelAccount(id=user_id, name=user.get("first_name", "")),
        conversation=ChannelAccount(id=chat_id),
        recipient=ChannelAccount(id="bot"),
        service_url="https://api.telegram.org",
    )

    try:
        await adapter.process_activity(activity, "", bot.on_turn)
    except Exception as exc:
        logger.error("Error processing Telegram update: %s", exc, exc_info=True)

    return Response(status_code=200)
