"""Azure Key Vault service client for runtime secret access.

In the PoC, secrets are injected via Container App Key Vault references
(environment variables resolved at startup).  This module provides an
optional async client for scenarios that require runtime secret reads,
such as on-demand rotation or dynamic secret retrieval.

:func:`resolve_secrets` can be called during app startup to populate
empty config fields from Key Vault, bridging the gap between env-var
injection and runtime secret resolution.

Usage::

    from app.services.key_vault import get_secret
    value = await get_secret("my-secret-name")
"""

import logging

from azure.identity.aio import DefaultAzureCredential
from azure.keyvault.secrets.aio import SecretClient

from app.config import settings

logger = logging.getLogger(__name__)

_client: SecretClient | None = None

# Maps config field names to their corresponding Key Vault secret names.
# Only fields that are *empty* at startup will be resolved from Key Vault.
_SECRET_MAP: dict[str, str] = {
    "ai_foundry_key": "ai-foundry-key",
    "cosmos_connection": "cosmos-connection",
    "blob_connection": "blob-connection",
    "bot_app_password": "bot-app-password",
    "telegram_bot_token": "telegram-bot-token",
}


def _get_client() -> SecretClient:
    """Return a singleton async Key Vault SecretClient."""
    global _client
    if _client is None:
        if not settings.key_vault_url:
            raise RuntimeError(
                "KEY_VAULT_URL is not configured. "
                "Set the key_vault_url setting or the KEY_VAULT_URL env var."
            )
        credential = DefaultAzureCredential()
        _client = SecretClient(
            vault_url=settings.key_vault_url,
            credential=credential,
        )
    return _client


async def get_secret(name: str) -> str:
    """Retrieve a secret value from Azure Key Vault by name.

    Args:
        name: The secret name (e.g. ``ai-foundry-key``).

    Returns:
        The secret value as a plain string.

    Raises:
        RuntimeError: If Key Vault URL is not configured.
        azure.core.exceptions.ResourceNotFoundError: If the secret does not exist.
    """
    client = _get_client()
    secret = await client.get_secret(name)
    logger.info("Retrieved secret '%s' from Key Vault.", name)
    return secret.value


async def resolve_secrets() -> None:
    """Populate empty config fields from Key Vault (best-effort).

    This is designed to be called once during application startup.
    Only fields listed in ``_SECRET_MAP`` that are currently empty on the
    ``settings`` object will be fetched.  Failures are logged but do not
    raise — the application can still start if some secrets are
    unavailable (they may not be needed in every environment).
    """
    if not settings.key_vault_url:
        logger.debug("KEY_VAULT_URL not set — skipping Key Vault secret resolution.")
        return

    resolved = 0
    for field, vault_name in _SECRET_MAP.items():
        current = getattr(settings, field, "")
        if current:
            continue  # already set via env var
        try:
            value = await get_secret(vault_name)
            # Pydantic v2 settings are normally frozen, but we need to
            # override them at startup for secret injection.
            object.__setattr__(settings, field, value)
            resolved += 1
            logger.info("Resolved '%s' from Key Vault.", field)
        except Exception as exc:
            logger.warning(
                "Could not resolve '%s' from Key Vault: %s", field, exc
            )

    logger.info("Key Vault resolution complete: %d secrets resolved.", resolved)
