"""
Gemini-powered embedding module — new google-genai SDK.
Uses text-embedding-004 with task_type optimization.

API change from google-generativeai:
  OLD: genai.embed_content(model=..., content=text, task_type=...)["embedding"]
  NEW: client.models.embed_content(model=..., contents=text,
           config=types.EmbedContentConfig(task_type=...)).embeddings[0].values
"""
import asyncio
import logging
from google.genai import types
from app.core.gemini_client import get_client

logger = logging.getLogger(__name__)

_embedding_model: str = "models/text-embedding-004"


def init_embedder(api_key: str, model: str) -> None:
    """Store the embedding model name. Client is shared via gemini_client."""
    global _embedding_model
    _embedding_model = model
    logger.info(f"Embedder configured with model: {model}")


async def embed_text(text: str, task_type: str = "RETRIEVAL_DOCUMENT") -> list[float]:
    """Embed a single text string."""
    client = get_client()
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(
        None,
        lambda: client.models.embed_content(
            model=_embedding_model,
            contents=text,
            config=types.EmbedContentConfig(task_type=task_type, output_dimensionality=768),
        )
    )
    # New SDK: result.embeddings is a list of ContentEmbedding objects
    return result.embeddings[0].values


async def embed_query(text: str) -> list[float]:
    """Embed a user query (separate task type for better retrieval quality)."""
    return await embed_text(text, task_type="RETRIEVAL_QUERY")


async def batch_embed(
    texts: list[str],
    task_type: str = "RETRIEVAL_DOCUMENT",
) -> list[list[float]]:
    """
    Batch embed texts — processes in chunks of 50 to stay within API limits.
    Gemini embedding API is fast; gentle sleep between batches to avoid rate limits.
    """
    results: list[list[float]] = []
    batch_size = 50
    for i in range(0, len(texts), batch_size):
        batch = texts[i: i + batch_size]
        tasks = [embed_text(t, task_type) for t in batch]
        batch_results = await asyncio.gather(*tasks)
        results.extend(batch_results)
        if i + batch_size < len(texts):
            await asyncio.sleep(0.1)  # gentle rate limiting
    return results
