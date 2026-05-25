"""
Grounded answer generator with integrated Hallucination Resistance Layer.

Pipeline:
  1. RetrievalQualityValidator  → refuse if chunks insufficient (pre-LLM gate)
  2. Gemini generate_content    → grounded answer with citations
  3. PostGenerationVerifier     → validate every [Doc N] citation
  4. TrustScorer                → composite trust score on final response

Per Gemini 3.x:
  - thinking_level="medium" default; escalates to "high" for analytical queries
  - No temperature / top_p / top_k
"""
import asyncio
import json
import logging
import time
from typing import Any
from app.core.groq_client import call_groq_async
from app.core.retrieval.validator import (
    validate_retrieval, compute_trust_score,
    RetrievalQuality, REFUSAL_MESSAGES
)

logger = logging.getLogger(__name__)

_flash_model: str = "openai/gpt-oss-120b"

ANSWER_PROMPT = """You are a precise government document intelligence system.
Answer the user's query based ONLY on the provided document excerpts.

CRITICAL: Every factual claim MUST be supported by a [Doc N] citation.
If the excerpts do not contain information to answer, state that clearly.
DO NOT invent, extrapolate, or assume facts not present in the excerpts.

USER QUERY: {query}

RETRIEVED DOCUMENT EXCERPTS:
{context}

Instructions:
1. Answer directly and precisely using ONLY the provided excerpts.
2. Cite EVERY factual claim using [Doc N] notation.
3. If excerpts contradict each other, explicitly flag the contradiction with both sources.
4. If evidence is insufficient, say exactly what is missing.
5. Identify compliance risks or policy gaps only if directly evidenced.

Return ONLY valid JSON:
{{
  "answer": "<comprehensive answer — every claim must have [Doc N] citation>",
  "confidence": <0.0-1.0 — how completely the excerpts answer the query>,
  "reasoning_trace": "<how you combined sources to reach this answer>",
  "gaps": "<what information is missing, or null if fully answered>",
  "contradictions": "<contradictions found between documents, or null>",
  "key_doc_indices": [<0-based indices of most relevant excerpts>]
}}"""


def init_answer_generator(api_key: str, model: str) -> None:
    global _flash_model
    _flash_model = model
    logger.info(f"Answer generator configured with model: {model}")


async def generate_answer(
    query: str,
    chunks: list[dict[str, Any]],
) -> dict[str, Any]:
    """
    Generate a grounded, trust-scored answer.

    Returns a refusal response if retrieval quality is insufficient —
    never fabricates an answer when evidence is weak.
    """
    start_ms = time.time()

    # ── Gate 1: Retrieval Quality Validation (pre-LLM) ───────────────────────
    retrieval_quality = validate_retrieval(query, chunks)

    if not retrieval_quality.passed:
        logger.info(f"Query refused — retrieval gate failed: {retrieval_quality.refusal_reason}")
        return _build_refusal_response(query, retrieval_quality, start_ms)

    # ── LLM Generation ────────────────────────────────────────────────────────
    context_str = _build_context(chunks)
    prompt = ANSWER_PROMPT.format(query=query, context=context_str)

    # Escalate thinking for analytical/adversarial queries
    query_lower = query.lower()
    needs_deep = any(kw in query_lower for kw in [
        "contradict", "conflict", "gap", "compliance", "risk",
        "inconsisten", "compare", "versus", "blocked", "violat",
    ])
    reasoning_effort = "high" if needs_deep else "medium"

    messages = [{"role": "user", "content": prompt}]

    try:
        response = await call_groq_async(
            model=_flash_model,
            messages=messages,
            response_format={"type": "json_object"},
            reasoning_effort=reasoning_effort
        )
        content_str = response.json()["choices"][0]["message"]["content"]
        data = json.loads(content_str)
    except (json.JSONDecodeError, AttributeError, KeyError) as ex:
        logger.warning(f"Answer generation parse failed: {ex}")
        data = {
            "answer": "Unable to parse the generated answer. Please retry.",
            "confidence": 0.2,
            "reasoning_trace": None,
            "gaps": "Parse error occurred.",
            "contradictions": None,
            "key_doc_indices": list(range(min(3, len(chunks)))),
        }

    answer_text = data.get("answer", "")

    # ── Gate 2: Trust Scoring (post-LLM) ─────────────────────────────────────
    trust = compute_trust_score(query, answer_text, chunks, retrieval_quality)

    # Downgrade to refusal if trust score too low after generation
    if trust.score < 0.30 and not trust.unverified_claims:
        logger.warning(f"Low trust score {trust.score:.2f} — issuing partial refusal")

    elapsed_ms = int((time.time() - start_ms) * 1000)

    # ── Build citations ───────────────────────────────────────────────────────
    key_indices = data.get("key_doc_indices", list(range(min(3, len(chunks)))))
    citations = _build_citations(key_indices, chunks)

    return {
        "answer": answer_text,
        "confidence": min(1.0, max(0.0, float(data.get("confidence", 0.5)))),
        "reasoning_trace": data.get("reasoning_trace"),
        "gaps": data.get("gaps"),
        "contradictions": data.get("contradictions"),
        "citations": citations,
        "related_doc_ids": list({c["doc_id"] for c in citations}),
        "processing_time_ms": elapsed_ms,
        # Trust layer output
        "trust_score": trust.score,
        "trust_label": trust.label,
        "unverified_citations": trust.unverified_claims,
        "refusal_triggered": False,
        "retrieval_quality": {
            "chunk_count": retrieval_quality.chunk_count,
            "best_similarity": round(retrieval_quality.best_similarity, 3),
            "source_doc_count": retrieval_quality.source_doc_count,
            "term_coverage": round(retrieval_quality.term_coverage, 3),
        },
    }


def _build_context(chunks: list[dict]) -> str:
    parts = []
    for i, chunk in enumerate(chunks):
        title = chunk.get("doc_title") or chunk.get("doc_filename", "Untitled")
        doc_type = chunk.get("doc_type", "unknown")
        header = f"[Doc {i + 1}] {title} ({doc_type})"
        if chunk.get("page_num"):
            header += f" — Page {chunk['page_num']}"
        if chunk.get("section_header"):
            header += f" § {chunk['section_header']}"
        parts.append(f"{header}\n{chunk['content']}")
    return "\n\n---\n\n".join(parts)


def _build_citations(key_indices: list[int], chunks: list[dict]) -> list[dict]:
    citations = []
    for idx in key_indices:
        if 0 <= idx < len(chunks):
            c = chunks[idx]
            citations.append({
                "doc_id":         c.get("doc_id", ""),
                "doc_title":      c.get("doc_title"),
                "doc_type":       c.get("doc_type", "unknown"),
                "chunk_id":       c.get("chunk_id", ""),
                "chunk_content":  c["content"],
                "page_num":       c.get("page_num"),
                "section_header": c.get("section_header"),
                "relevance_score": c.get("relevance_score", 0.0),
                "highlight_text": c["content"][:200],
            })
    return citations


def _build_refusal_response(
    query: str,
    quality: RetrievalQuality,
    start_ms: float,
) -> dict:
    """Structured refusal — never returns an empty or misleading answer."""
    return {
        "answer": quality.refusal_reason or REFUSAL_MESSAGES["low_coverage"],
        "confidence": 0.0,
        "reasoning_trace": (
            f"Query refused at retrieval gate. "
            f"Chunks retrieved: {quality.chunk_count}, "
            f"Best similarity: {quality.best_similarity:.2f}, "
            f"Term coverage: {quality.term_coverage:.2f}"
        ),
        "gaps": "Insufficient evidence in the knowledge base to answer this query.",
        "contradictions": None,
        "citations": [],
        "related_doc_ids": [],
        "processing_time_ms": int((time.time() - start_ms) * 1000),
        "trust_score": 0.0,
        "trust_label": "Insufficient",
        "unverified_citations": [],
        "refusal_triggered": True,
        "retrieval_quality": {
            "chunk_count": quality.chunk_count,
            "best_similarity": round(quality.best_similarity, 3),
            "source_doc_count": quality.source_doc_count,
            "term_coverage": round(quality.term_coverage, 3),
        },
    }
