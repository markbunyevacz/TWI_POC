"""Integration tests for the FastAPI /api/messages endpoint.

Uses httpx.AsyncClient against the real FastAPI app with auth and
external services mocked out, verifying the HTTP layer works end-to-end.
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock

import httpx


BOT_ACTIVITY_MESSAGE = {
    "type": "message",
    "id": "test-activity-001",
    "timestamp": "2026-03-13T10:00:00.000Z",
    "channelId": "msteams",
    "from": {"id": "test-user-001", "name": "Test User"},
    "conversation": {"id": "test-conv-001"},
    "recipient": {"id": "bot-id-001", "name": "agentize AI"},
    "text": "Szia!",
    "serviceUrl": "https://smba.trafficmanager.net/emea/",
}

BOT_ACTIVITY_TWI = {
    **BOT_ACTIVITY_MESSAGE,
    "id": "test-activity-002",
    "text": "Készíts TWI utasítást a CNC-01 gép napi karbantartásáról",
}


def _make_mock_claims(authenticated: bool = True):
    claims = MagicMock()
    claims.is_authenticated = authenticated
    return claims


@pytest.fixture
def skip_auth():
    """Bypass JWT token validation and Bot Framework adapter auth."""
    with patch("app.main.settings") as mock_settings:
        mock_settings.bot_app_id = ""
        mock_settings.bot_app_password = ""
        mock_settings.channel_auth_tenant = ""
        mock_settings.environment = "poc"
        mock_settings.log_level = "INFO"
        mock_settings.applicationinsights_connection_string = ""
        yield mock_settings


@pytest.fixture
def mock_adapter_process():
    """Mock the adapter.process_activity to avoid real Bot Framework calls."""
    with patch("app.main.adapter") as mock_adapter:
        mock_adapter.process_activity = AsyncMock(return_value=None)
        mock_adapter.on_turn_error = None
        yield mock_adapter


@pytest.fixture
def auth_pass():
    """Allow auth through by mocking JwtTokenValidation."""
    with patch("app.main.settings") as mock_settings:
        mock_settings.bot_app_id = "test-app-id"
        mock_settings.bot_app_password = "test-password"
        mock_settings.channel_auth_tenant = ""
        mock_settings.environment = "poc"
        mock_settings.log_level = "INFO"
        mock_settings.applicationinsights_connection_string = ""
        with patch(
            "app.main.JwtTokenValidation.authenticate_request",
            new=AsyncMock(return_value=_make_mock_claims(True)),
        ):
            yield


class TestHealthEndpoint:
    @pytest.mark.asyncio
    async def test_health_returns_200(self):
        from app.main import app

        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "healthy"

    @pytest.mark.asyncio
    async def test_root_returns_service_info(self):
        from app.main import app

        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get("/")
        assert resp.status_code == 200
        assert "agentize" in resp.json()["service"]


class TestMessagesEndpoint:
    @pytest.mark.asyncio
    async def test_unauthenticated_returns_401(self, auth_pass):
        """Without auth mock, a bare request should get 401."""
        from app.main import app

        with patch("app.main.settings") as ms:
            ms.bot_app_id = "test-app-id"
            ms.bot_app_password = "test-password"
            ms.channel_auth_tenant = ""
            ms.environment = "poc"
            ms.log_level = "INFO"
            ms.applicationinsights_connection_string = ""
            with patch(
                "app.main.JwtTokenValidation.authenticate_request",
                new=AsyncMock(return_value=_make_mock_claims(False)),
            ):
                async with httpx.AsyncClient(
                    transport=httpx.ASGITransport(app=app), base_url="http://test"
                ) as client:
                    resp = await client.post("/api/messages", json=BOT_ACTIVITY_MESSAGE)
                assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_valid_message_returns_200(self, skip_auth, mock_adapter_process):
        """With auth skipped, a valid activity should process and return 200."""
        from app.main import app

        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.post("/api/messages", json=BOT_ACTIVITY_MESSAGE)
        assert resp.status_code == 200
        mock_adapter_process.process_activity.assert_called_once()

    @pytest.mark.asyncio
    async def test_auth_pass_with_valid_token(self, auth_pass, mock_adapter_process):
        """With mocked JWT validation passing, message should be processed."""
        from app.main import app

        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.post("/api/messages", json=BOT_ACTIVITY_TWI)
        assert resp.status_code == 200
        mock_adapter_process.process_activity.assert_called_once()

    @pytest.mark.asyncio
    async def test_invalid_activity_processed_without_crash(
        self, skip_auth, mock_adapter_process
    ):
        """An activity with minimal fields should still reach the adapter."""
        from app.main import app

        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            resp = await client.post(
                "/api/messages",
                json={"type": "event", "name": "test"},
            )
        assert resp.status_code == 200
