"""Azure Key Vault service for programmatic secret access."""

import logging
from typing import Any

from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient

from app.config import settings

logger = logging.getLogger(__name__)

_client: SecretClient | None = None


def _get_client() -> SecretClient:
    """Get or create the Key Vault client singleton."""
    global _client
    if _client is None:
        # Use the Key Vault URI from settings or construct from environment
        # For now, we'll use a placeholder - in production this would come from
        # the infrastructure outputs or environment variable
        vault_uri = getattr(settings, "key_vault_uri", None) or ""
        if vault_uri:
            credential = DefaultAzureCredential()
            _client = SecretClient(vault_url=vault_uri, credential=credential)
        else:
            logger.warning("Key Vault URI not configured - secret operations will fail")
    return _client


class KeyVaultService:
    """Service for accessing secrets from Azure Key Vault."""

    def __init__(self) -> None:
        self._client = _get_client()

    async def get_secret(self, secret_name: str) -> str | None:
        """Retrieve a secret value by name."""
        try:
            client = _get_client()
            if client is None:
                logger.error("Key Vault client not initialized")
                return None
            secret = client.get_secret(secret_name)
            return secret.value
        except Exception as exc:  # noqa: BLE001
            logger.error("Failed to get secret %s: %s", secret_name, exc)
            return None

    async def set_secret(self, secret_name: str, value: str, **kwargs: Any) -> bool:
        """Set a secret value by name."""
        try:
            client = _get_client()
            if client is None:
                logger.error("Key Vault client not initialized")
                return False
            client.set_secret(secret_name, value, **kwargs)
            logger.info("Secret %s set successfully", secret_name)
            return True
        except Exception as exc:  # noqa: BLE001
            logger.error("Failed to set secret %s: %s", secret_name, exc)
            return False

    async def delete_secret(self, secret_name: str) -> bool:
        """Delete a secret by name."""
        try:
            client = _get_client()
            if client is None:
                logger.error("Key Vault client not initialized")
                return False
            client.begin_delete_secret(secret_name)
            logger.info("Secret %s deletion initiated", secret_name)
            return True
        except Exception as exc:  # noqa: BLE001
            logger.error("Failed to delete secret %s: %s", secret_name, exc)
            return False

    async def list_secrets(self) -> list[dict[str, Any]] | None:
        """List all secret names in the vault."""
        try:
            client = _get_client()
            if client is None:
                logger.error("Key Vault client not initialized")
                return None
            secrets = client.list_properties_of_secrets()
            return [
                {"name": s.name, "enabled": s.enabled, "created": s.created_on}
                for s in secrets
            ]
        except Exception as exc:  # noqa: BLE001
            logger.error("Failed to list secrets: %s", exc)
            return None
