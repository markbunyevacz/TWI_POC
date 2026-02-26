import logging

from fastapi import FastAPI, Request, Response
from botbuilder.core import BotFrameworkAdapter, BotFrameworkAdapterSettings
from botbuilder.schema import Activity
from botframework.connector.auth import JwtTokenValidation, SimpleCredentialProvider

from app.config import settings
from app.bot.bot_handler import AgentizeBotHandler

logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s %(levelname)s %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)

if settings.applicationinsights_connection_string:
    try:
        from azure.monitor.opentelemetry import configure_azure_monitor
        configure_azure_monitor(
            connection_string=settings.applicationinsights_connection_string
        )
        logger.info("Application Insights telemetry initialized successfully.")
    except Exception as e:
        logger.error("Failed to initialize Application Insights: %s", e)

app = FastAPI(
    title="agentize.eu PoC Backend",
    version="0.1.0",
    docs_url="/docs" if settings.environment == "poc" else None,
    redoc_url="/redoc" if settings.environment == "poc" else None,
)

# Bot Framework adapter
_adapter_settings = BotFrameworkAdapterSettings(
    app_id=settings.bot_app_id,
    app_password=settings.bot_app_password,
)
adapter = BotFrameworkAdapter(_adapter_settings)

# Bot handler (singleton — holds the LangGraph graph)
bot = AgentizeBotHandler()


async def _on_error(context, error: Exception) -> None:
    logger.error("Bot adapter error: %s", error, exc_info=True)
    await context.send_activity("Hiba történt. Kérlek próbáld újra.")


adapter.on_turn_error = _on_error


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@app.post("/api/messages")
async def messages(request: Request) -> Response:
    """Bot Framework messaging endpoint — called by Azure Bot Service."""
    body = await request.json()
    activity = Activity().deserialize(body)
    auth_header = request.headers.get("Authorization", "")

    # Explicit Entra ID token validation
    if settings.bot_app_id:
        try:
            credentials = SimpleCredentialProvider(settings.bot_app_id, settings.bot_app_password)
            claims = await JwtTokenValidation.authenticate_request(
                activity, auth_header, credentials, ""
            )
            if not claims.is_authenticated:
                logger.warning("Unauthenticated request to /api/messages")
                return Response(status_code=401)
        except Exception as e:
            logger.error("Token validation failed: %s", e)
            return Response(status_code=401)

    response = await adapter.process_activity(
        activity, auth_header, bot.on_turn
    )

    if response:
        return Response(
            content=response.body,
            status_code=response.status,
            headers=dict(response.headers) if response.headers else {},
        )
    return Response(status_code=200)


@app.get("/health")
async def health() -> dict:
    return {"status": "healthy", "environment": settings.environment}


@app.get("/")
async def root() -> dict:
    return {"service": "agentize.eu PoC Backend", "version": "0.1.0"}
