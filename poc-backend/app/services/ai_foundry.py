import logging
from azure.ai.inference.aio import ChatCompletionsClient as AsyncChatCompletionsClient
from azure.core.credentials import AzureKeyCredential

from app.config import settings

logger = logging.getLogger(__name__)

_client: AsyncChatCompletionsClient | None = None


def _get_client() -> AsyncChatCompletionsClient:
    global _client
    if _client is None:
        _client = AsyncChatCompletionsClient(
            endpoint=settings.ai_foundry_endpoint,
            credential=AzureKeyCredential(settings.ai_foundry_key),
        )
    return _client


async def call_llm(
    prompt: str,
    system_prompt: str | None = None,
    temperature: float | None = None,
    max_tokens: int | None = None,
) -> str:
    """Call Azure AI Foundry (Mistral Large / GPT-4o) and return the response text."""
    client = _get_client()

    messages: list[dict] = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})

    response = await client.complete(
        messages=messages,
        model=settings.ai_model,
        temperature=temperature if temperature is not None else settings.ai_temperature,
        max_tokens=max_tokens if max_tokens is not None else settings.ai_max_tokens,
    )

    content: str = response.choices[0].message.content
    usage = response.usage
    logger.info(
        "LLM call: model=%s, input_tokens=%d, output_tokens=%d",
        settings.ai_model,
        usage.prompt_tokens,
        usage.completion_tokens,
    )
    return content
