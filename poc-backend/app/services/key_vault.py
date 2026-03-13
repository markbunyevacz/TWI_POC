"""Azure Key Vault service for programmatic secret access.

The ``azure-keyvault-secrets`` SDK is synchronous. All public methods use
``asyncio.to_thread`` to avoid blocking the event loop.
"""

import asyncio
import logging
from typing import Any

from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient

from app.config import settings

logger = logging.getLogger(__name__)

_client: SecretClient | None = None


def _get_client() -> SecretClient | None:
    """Get or create the Key Vault client singleton."""
    global _client
    if _client is None:
        vault_uri = settings.key_vault_uri or settings.key_vault_url
        if vault_uri:
            credential = DefaultAzureCredential()
            _client = SecretClient(vault_url=vault_uri, credential=credential)
        else:
            logger.warning(
                "Key Vault URI not configured (KEY_VAULT_URI / KEY_VAULT_URL). "
                "Secret operations will be unavailable."
            )
    return _client


class KeyVaultService:
    """Service for accessing secrets from Azure Key Vault."""

    def __init__(self) -> None:
        self._client = _get_client()

    async def get_secret(self, secret_name: str) -> str | None:
        """Retrieve a secret value by name."""
        client = _get_client()
        if client is None:
            logger.error("Key Vault client not initialized")
            return None
        try:
            secret = await asyncio.to_thread(client.get_secret, secret_name)
            return secret.value
        except Exception as exc:  # noqa: BLE001
            logger.error("Failed to get secret %s: %s", secret_name, exc)
            return None

    async def set_secret(self, secret_name: str, value: str, **kwargs: Any) -> bool:
        """Set a secret value by name."""
        client = _get_client()
        if client is None:
            logger.error("Key Vault client not initialized")
            return False
        try:
            await asyncio.to_thread(client.set_secret, secret_name, value, **kwargs)
            logger.info("Secret %s set successfully", secret_name)
            return True
        except Exception as exc:  # noqa: BLE001
            logger.error("Failed to set secret %s: %s", secret_name, exc)
            return False

    async def delete_secret(self, secret_name: str) -> bool:
        """Delete a secret by name."""
        client = _get_client()
        if client is None:
            logger.error("Key Vault client not initialized")
            return False
        try:
            await asyncio.to_thread(client.begin_delete_secret, secret_name)
            logger.info("Secret %s deletion initiated", secret_name)
            return True
        except Exception as exc:  # noqa: BLE001
            logger.error("Failed to delete secret %s: %s", secret_name, exc)
            return False

    async def list_secrets(self) -> list[dict[str, Any]] | None:
        """List all secret names in the vault."""
        client = _get_client()
        if client is None:
            logger.error("Key Vault client not initialized")
            return None
        try:
            props = await asyncio.to_thread(
                lambda: list(client.list_properties_of_secrets())
            )
            return [
                {"name": s.name, "enabled": s.enabled, "created": s.created_on}
                for s in props
            ]
        except Exception as exc:  # noqa: BLE001
            logger.error("Failed to list secrets: %s", exc)
            return None
