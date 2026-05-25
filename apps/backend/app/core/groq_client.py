"""
Groq API client with tenacity retry.
Uses HTTPX to communicate with the Groq OpenAI-compatible endpoints.
"""
import httpx
import logging
import asyncio
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log,
)

logger = logging.getLogger(__name__)

_api_key: str | None = None
_client: httpx.AsyncClient | None = None


def init_groq(api_key: str) -> None:
    """Initialize the Groq HTTP client. Called once on app startup."""
    global _api_key, _client
    _api_key = api_key
    _client = httpx.AsyncClient(
        base_url="https://api.groq.com/openai/v1",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        timeout=60.0
    )
    logger.info("Groq HTTP client initialized")


def get_client() -> httpx.AsyncClient:
    """Return the shared Groq client. Raises if not initialized."""
    if _client is None:
        raise RuntimeError("Groq client not initialized — call init_groq() first")
    return _client


@retry(
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=1.5, min=2, max=30),
    retry=retry_if_exception_type((httpx.RequestError, httpx.HTTPStatusError)),
    before_sleep=before_sleep_log(logger, logging.WARNING),
    reraise=True,
)
async def call_groq_async(model: str, messages: list[dict], response_format: dict | None = None, **kwargs) -> httpx.Response:
    """
    Asynchronous Groq API call with exponential backoff retry.
    """
    client = get_client()
    payload = {
        "model": model,
        "messages": messages,
    }
    if response_format:
        payload["response_format"] = response_format
    
    payload.update(kwargs)

    response = await client.post("/chat/completions", json=payload)
    response.raise_for_status()
    return response
