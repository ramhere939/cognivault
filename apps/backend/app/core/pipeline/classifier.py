"""
Document classifier — new google-genai SDK.

Uses gemini-3.5-flash with JSON response mode to classify documents in one call.
Per Gemini 3.x guidance:
  - No temperature / top_p / top_k (removed — not recommended for Gemini 3.x)
  - Uses thinking_level="low" (fast, structured output task)
  - response_mime_type="application/json" for reliable JSON parsing
"""
import asyncio
import json
import logging
from typing import Any
from app.core.groq_client import call_groq_async

logger = logging.getLogger(__name__)

_flash_model: str = "openai/gpt-oss-120b"

DOC_TYPES = [
    "policy", "invoice", "contract", "circular",
    "meeting_note", "scheme", "compliance", "procurement", "unknown",
]

CLASSIFIER_PROMPT = """You are a government document classifier. Analyze the provided text and extract metadata.

Classify the document type as one of: {doc_types}

Return ONLY valid JSON matching this schema exactly:
{{
  "doc_type": "<one of the types above>",
  "title": "<document title or null>",
  "summary": "<2-3 sentence summary>",
  "doc_date": "<YYYY-MM-DD or null>",
  "author": "<author or issuing authority or null>",
  "department": "<government department or ministry or null>",
  "keywords": ["<keyword1>", "<keyword2>", ...],
  "confidence": <0.0-1.0>
}}

Document text (first 4000 characters):
{text}"""


def init_classifier(api_key: str, model: str) -> None:
    global _flash_model
    _flash_model = model
    logger.info(f"Classifier configured with model: {model}")


async def classify_document(text: str) -> dict[str, Any]:
    """Classify a document and extract metadata using Groq."""
    prompt = CLASSIFIER_PROMPT.format(
        doc_types=", ".join(DOC_TYPES),
        text=text[:4000],
    )

    messages = [{"role": "user", "content": prompt}]

    try:
        response = await call_groq_async(
            model=_flash_model,
            messages=messages,
            response_format={"type": "json_object"}
        )
        content_str = response.json()["choices"][0]["message"]["content"]
        data = json.loads(content_str)
        if data.get("doc_type") not in DOC_TYPES:
            data["doc_type"] = "unknown"
        return data
    except (json.JSONDecodeError, AttributeError) as e:
        logger.warning(f"Classifier JSON parse failed: {e} — using fallback")
        return {
            "doc_type": "unknown",
            "title": None,
            "summary": None,
            "doc_date": None,
            "author": None,
            "department": None,
            "keywords": [],
            "confidence": 0.0,
        }
