"""
Refined ontology: replaces DEPENDS_ON / RELATES_TO / MENTIONS with
precise, operationally meaningful edge types.

SUPERSESSION CHAIN (document lifecycle):
  SUPERSEDES    → A fully replaces B
  AMENDS        → A modifies specific clauses of B
  REVOKES       → A cancels B with no replacement (compliance gap risk)

OPERATIONAL CHAIN (execution dependency):
  IMPLEMENTS    → A operationalizes policy in B
  MANDATED_BY   → A is legally required by regulation in B
  ENABLES       → A approval/completion is prerequisite for B
  BLOCKS        → A open issue prevents B from proceeding

EVIDENCE CHAIN (epistemic):
  REFERENCES    → A cites B for context (informational)
  VERIFIED_BY   → B independently confirms claims in A
  CONTRADICTS   → A conflicts with a directive in B

FINANCIAL / PROCUREMENT:
  PROCURES_UNDER → Invoice/contract executed under policy in B
  AUDITED_BY     → Financial doc subject to audit framework in B
"""

import asyncio
import json
import logging
from typing import Any
from app.core.groq_client import call_groq_async

logger = logging.getLogger(__name__)

_flash_model: str = "openai/gpt-oss-120b"

ENTITY_TYPES = [
    "PERSON", "ORG", "DATE", "AMOUNT",
    "POLICY_ID", "LOCATION", "REGULATION", "KEYWORD",
]

# Refined relation labels — RELATES_TO / DEPENDS_ON / MENTIONS removed
RELATION_LABELS = [
    # Supersession chain
    "SUPERSEDES", "AMENDS", "REVOKES",
    # Operational chain
    "IMPLEMENTS", "MANDATED_BY", "ENABLES", "BLOCKS",
    # Evidence chain
    "REFERENCES", "VERIFIED_BY", "CONTRADICTS",
    # Financial
    "PROCURES_UNDER", "AUDITED_BY",
]

# Confidence thresholds — each edge type requires a minimum to be stored
EDGE_CONFIDENCE_THRESHOLDS = {
    "SUPERSEDES":     0.80,
    "REVOKES":        0.85,
    "AMENDS":         0.75,
    "CONTRADICTS":    0.85,  # high bar — avoid false positives
    "IMPLEMENTS":     0.70,
    "MANDATED_BY":    0.75,
    "ENABLES":        0.65,
    "BLOCKS":         0.70,
    "REFERENCES":     0.50,
    "PROCURES_UNDER": 0.75,
    "VERIFIED_BY":    0.70,
    "AUDITED_BY":     0.72,
}

ENTITY_EXTRACTION_PROMPT = """Extract named entities from this government document text.

Return ONLY valid JSON:
{{
  "entities": [
    {{
      "name": "<entity name>",
      "entity_type": "<one of: {entity_types}>",
      "normalized": "<normalized form or null>",
      "evidence_quote": "<exact short quote proving this entity, max 100 chars>",
      "confidence": <0.0-1.0>
    }}
  ]
}}

Focus on: policy IDs, regulation references, amounts, officials, organizations, dates.
Deduplicate — only include each unique entity once.
Limit to top 20 most significant entities.

Text:
{text}"""

RELATIONSHIP_PROMPT = """You are analyzing relationships between two government documents.

Document A: {doc_a_title} ({doc_a_type})
Summary A: {doc_a_summary}
Key entities A: {entities_a}

Document B: {doc_b_title} ({doc_b_type})
Summary B: {doc_b_summary}
Key entities B: {entities_b}

Determine if Document A has a significant formal relationship with Document B.

RELATION TYPES (use only these):
- SUPERSEDES: A fully and formally replaces B (strongest — requires explicit language)
- AMENDS: A modifies specific clauses/sections of B
- REVOKES: A cancels B entirely with no replacement (creates a compliance gap)
- IMPLEMENTS: A operationalizes or executes the policy framework in B
- MANDATED_BY: A is legally required or directed by the regulation/policy in B
- ENABLES: Completion/approval of A is a prerequisite for B to proceed
- BLOCKS: An open issue in A prevents B from proceeding
- REFERENCES: A cites B for context, authority, or background (informational)
- VERIFIED_BY: B independently confirms or validates claims made in A
- CONTRADICTS: A directly conflicts with a specific directive or ruling in B
- PROCURES_UNDER: A (invoice/contract) was executed under the procurement framework in B
- AUDITED_BY: A (financial doc) is subject to the audit/compliance framework in B

DO NOT use RELATES_TO, DEPENDS_ON, or MENTIONS — they are too vague.

Return ONLY valid JSON:
{{
  "has_relationship": true/false,
  "relation_label": "<one of the above or null>",
  "confidence": <0.0-1.0>,
  "evidence_quote": "<direct quote proving the relationship, or null>",
  "explanation": "<one sentence explanation>",
  "operational_risk": "<compliance/operational risk this relationship implies, or null>"
}}"""


def init_entity_extractor(api_key: str, model: str) -> None:
    global _flash_model
    _flash_model = model
    logger.info(f"Entity extractor configured with model: {model}")


async def extract_entities(text: str, doc_type: str = "unknown") -> list[dict[str, Any]]:
    """Extract typed entities from document text."""
    prompt = ENTITY_EXTRACTION_PROMPT.format(
        entity_types=", ".join(ENTITY_TYPES),
        text=text[:6000],
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
        return [e for e in data.get("entities", []) if e.get("entity_type") in ENTITY_TYPES]
    except (json.JSONDecodeError, AttributeError) as ex:
        logger.warning(f"Entity extraction parse failed: {ex}")
        return []


async def detect_relationship(
    doc_a: dict[str, Any],
    doc_b: dict[str, Any],
    shared_entities: list[str] = None,
) -> dict[str, Any] | None:
    """
    Detect precise relationship between two documents.
    Entity-overlap gate must be satisfied before calling this.
    Returns None if no relationship meets confidence threshold.
    """
    def _fmt_entities(entities: list[dict]) -> str:
        return ", ".join(
            f"{e.get('entity_type', '?')}:{e.get('name', '')}"
            for e in entities[:10]
        )

    prompt = RELATIONSHIP_PROMPT.format(
        doc_a_title=doc_a.get("title") or doc_a.get("filename", "Doc A"),
        doc_a_type=doc_a.get("doc_type", "unknown"),
        doc_a_summary=doc_a.get("summary") or "No summary available",
        entities_a=_fmt_entities(doc_a.get("entities", [])),
        doc_b_title=doc_b.get("title") or doc_b.get("filename", "Doc B"),
        doc_b_type=doc_b.get("doc_type", "unknown"),
        doc_b_summary=doc_b.get("summary") or "No summary available",
        entities_b=_fmt_entities(doc_b.get("entities", [])),
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
    except (json.JSONDecodeError, AttributeError) as ex:
        logger.warning(f"Relationship detection parse failed: {ex}")
        return None

    if not data.get("has_relationship"):
        return None

    relation = data.get("relation_label")
    confidence = data.get("confidence", 0.0)

    # Enforce per-edge-type confidence thresholds
    min_confidence = EDGE_CONFIDENCE_THRESHOLDS.get(relation, 0.70)
    if confidence < min_confidence:
        logger.debug(f"Relationship {relation} rejected: {confidence:.2f} < {min_confidence}")
        return None

    if relation not in RELATION_LABELS:
        logger.warning(f"Unknown relation label: {relation}")
        return None

    return {
        "relation_label": relation,
        "confidence": confidence,
        "evidence_quote": data.get("evidence_quote"),
        "explanation": data.get("explanation"),
        "operational_risk": data.get("operational_risk"),
    }
