"""
Gemini client with tenacity retry — production-grade resilience.
Wraps the raw google-genai client with exponential backoff on rate limits.
"""
import logging
from google import genai
from google.genai import types  # noqa: F401
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log,
)

logger = logging.getLogger(__name__)

_client: genai.Client | None = None


def init_gemini(api_key: str) -> None:
    """Initialize the shared Gemini client. Called once on app startup."""
    global _client
    _client = genai.Client(api_key=api_key)
    logger.info("Gemini client initialized (google-genai SDK v2)")


def get_client() -> genai.Client:
    """Return the shared Gemini client. Raises if not initialized."""
    if _client is None:
        raise RuntimeError("Gemini client not initialized — call init_gemini() first")
    return _client


@retry(
    stop=stop_after_attempt(7),
    wait=wait_exponential(multiplier=2, min=10, max=90),
    retry=retry_if_exception_type((Exception,)),
    before_sleep=before_sleep_log(logger, logging.WARNING),
    reraise=True,
)
def call_gemini_sync(client: genai.Client, **kwargs):
    """
    Synchronous Gemini API call with exponential backoff retry.

    Use inside run_in_executor for async contexts:
      response = await loop.run_in_executor(
          None, lambda: call_gemini_sync(client, model=..., contents=..., config=...)
      )

    Retries on any exception (rate limits, transient 500s) up to 3 times.
    Waits 2s, 4s, 8s between attempts.
    """
    return client.models.generate_content(**kwargs)
