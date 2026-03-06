"""Azure Key Vault service client for runtime secret access.

In the PoC, secrets are injected via Container App Key Vault references
(environment variables resolved at startup).  This module provides an
optional async client for scenarios that require runtime secret reads,
such as on-demand rotation or dynamic secret retrieval.

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
