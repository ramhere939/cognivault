"""
Hallucination Resistance Layer

Pipeline:
  1. RetrievalQualityValidator  → gates on chunk quality before LLM call
  2. PostGenerationVerifier     → validates citations after LLM generates
  3. TrustScorer                → computes composite trust score

Design principle: prefer "I don't have evidence" over confident fabrication.
Every claim in the answer must be traceable to a retrieved chunk.
"""
import logging
import re
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

# ── Thresholds ─────────────────────────────────────────────────────────────
REFUSAL_THRESHOLDS = {
    "min_chunks":           2,     # refuse if < 2 chunks retrieved
    "min_best_similarity":  0.55,  # refuse if best chunk score < 0.55
    "min_term_coverage":    0.35,  # refuse if <35% query terms in chunks
    "min_source_docs":      1,     # need at least 1 distinct source doc
}

TRUST_WEIGHTS = {
    "retrieval_quality":     0.30,
    "citation_verification": 0.40,
    "source_diversity":      0.15,
    "entity_coverage":       0.15,
}

# Refusal messages — specific, professional, non-apologetic
REFUSAL_MESSAGES = {
    "no_chunks":       "No relevant documents were found in the knowledge base for this query.",
    "low_similarity":  "The available documents do not contain sufficiently relevant information to answer this question.",
    "low_coverage":    "This query references concepts that do not appear in any indexed document.",
    "entity_missing":  "The referenced entity does not appear in any indexed document.",
}


# ── Data Structures ─────────────────────────────────────────────────────────

@dataclass
class RetrievalQuality:
    chunk_count:      int
    best_similarity:  float
    avg_similarity:   float
    source_doc_count: int
    term_coverage:    float
    passed:           bool
    refusal_reason:   str | None = None

    @property
    def quality_score(self) -> float:
        """0-1 score representing retrieval quality."""
        if not self.passed:
            return 0.0
        return min(1.0, (
            min(self.chunk_count / 5, 1.0) * 0.3 +
            min(self.best_similarity, 1.0) * 0.4 +
            min(self.source_doc_count / 3, 1.0) * 0.15 +
            min(self.term_coverage, 1.0) * 0.15
        ))


@dataclass
class CitationVerification:
    total_citations:    int
    verified_citations: int
    suspicious_indices: list[int] = field(default_factory=list)

    @property
    def verification_score(self) -> float:
        if self.total_citations == 0:
            return 1.0  # no citations to verify — neutral
        return self.verified_citations / self.total_citations


@dataclass
class TrustScore:
    score:               float        # 0-1 composite
    label:               str          # "High" | "Moderate" | "Low" | "Insufficient"
    retrieval_quality:   RetrievalQuality
    citation_verification: CitationVerification
    unverified_claims:   list[str]
    refusal_triggered:   bool
    refusal_reason:      str | None


# ── Validator ───────────────────────────────────────────────────────────────

class RetrievalQualityValidator:
    """
    Gate 1: Run BEFORE the LLM call.
    Refuses to proceed if retrieved chunks are insufficient.
    """

    def validate(self, query: str, chunks: list[dict]) -> RetrievalQuality:
        if not chunks:
            return RetrievalQuality(
                chunk_count=0, best_similarity=0.0, avg_similarity=0.0,
                source_doc_count=0, term_coverage=0.0,
                passed=False, refusal_reason=REFUSAL_MESSAGES["no_chunks"]
            )

        scores = [c.get("relevance_score", 0.0) for c in chunks]
        best_sim = max(scores)
        avg_sim = sum(scores) / len(scores)
        source_docs = len({c.get("doc_id") for c in chunks if c.get("doc_id")})

        # Term coverage: what fraction of query tokens appear in chunks
        query_tokens = set(re.findall(r'\b\w{3,}\b', query.lower()))
        chunk_text = " ".join(c.get("content", "") for c in chunks).lower()
        covered = sum(1 for t in query_tokens if t in chunk_text)
        coverage = covered / len(query_tokens) if query_tokens else 1.0

        # Check each refusal condition
        if len(chunks) < REFUSAL_THRESHOLDS["min_chunks"]:
            return RetrievalQuality(
                chunk_count=len(chunks), best_similarity=best_sim,
                avg_similarity=avg_sim, source_doc_count=source_docs,
                term_coverage=coverage, passed=False,
                refusal_reason=REFUSAL_MESSAGES["low_similarity"]
            )

        if best_sim < REFUSAL_THRESHOLDS["min_best_similarity"]:
            return RetrievalQuality(
                chunk_count=len(chunks), best_similarity=best_sim,
                avg_similarity=avg_sim, source_doc_count=source_docs,
                term_coverage=coverage, passed=False,
                refusal_reason=REFUSAL_MESSAGES["low_similarity"]
            )

        if coverage < REFUSAL_THRESHOLDS["min_term_coverage"]:
            return RetrievalQuality(
                chunk_count=len(chunks), best_similarity=best_sim,
                avg_similarity=avg_sim, source_doc_count=source_docs,
                term_coverage=coverage, passed=False,
                refusal_reason=REFUSAL_MESSAGES["low_coverage"]
            )

        return RetrievalQuality(
            chunk_count=len(chunks), best_similarity=best_sim,
            avg_similarity=avg_sim, source_doc_count=source_docs,
            term_coverage=coverage, passed=True
        )


class PostGenerationVerifier:
    """
    Gate 2: Run AFTER the LLM generates an answer.
    Verifies every [Doc N] citation traces to a real retrieved chunk.
    """

    def verify(self, answer: str, chunks: list[dict]) -> CitationVerification:
        cited_indices = [int(m) - 1 for m in re.findall(r'\[Doc\s*(\d+)\]', answer)]
        if not cited_indices:
            return CitationVerification(
                total_citations=0, verified_citations=0
            )

        suspicious = []
        verified = 0

        for idx in cited_indices:
            if idx < 0 or idx >= len(chunks):
                suspicious.append(idx + 1)
                logger.warning(f"Citation [Doc {idx+1}] references non-existent chunk")
                continue

            chunk = chunks[idx]
            chunk_text = chunk.get("content", "").lower()

            # Find the sentence containing the citation in the answer
            # and check if it has lexical overlap with the chunk
            pattern = rf'[^.!?]*\[Doc\s*{idx+1}\][^.!?]*[.!?]?'
            matches = re.findall(pattern, answer, re.IGNORECASE)
            claim_text = " ".join(matches).lower()

            claim_tokens = set(re.findall(r'\b\w{4,}\b', claim_text))
            claim_tokens -= {f"doc", str(idx + 1)}  # remove citation noise

            if not claim_tokens:
                verified += 1  # can't verify, give benefit of doubt
                continue

            chunk_tokens = set(re.findall(r'\b\w{4,}\b', chunk_text))
            overlap = len(claim_tokens & chunk_tokens) / len(claim_tokens)

            if overlap >= 0.25:  # 25% token overlap is a reasonable threshold
                verified += 1
            else:
                suspicious.append(idx + 1)
                logger.warning(
                    f"Citation [Doc {idx+1}] low overlap: {overlap:.2f} — "
                    f"claim_tokens={list(claim_tokens)[:5]}"
                )

        return CitationVerification(
            total_citations=len(cited_indices),
            verified_citations=verified,
            suspicious_indices=suspicious,
        )


class TrustScorer:
    """Computes composite trust score from retrieval + citation quality."""

    def __init__(self):
        self.validator = RetrievalQualityValidator()
        self.verifier = PostGenerationVerifier()

    def compute(
        self,
        query: str,
        answer: str,
        chunks: list[dict],
        retrieval_quality: RetrievalQuality,
    ) -> TrustScore:
        if not retrieval_quality.passed:
            return TrustScore(
                score=0.0, label="Insufficient",
                retrieval_quality=retrieval_quality,
                citation_verification=CitationVerification(0, 0),
                unverified_claims=[],
                refusal_triggered=True,
                refusal_reason=retrieval_quality.refusal_reason,
            )

        citation_result = self.verifier.verify(answer, chunks)

        # Source diversity: prefer answers from multiple documents
        source_doc_count = retrieval_quality.source_doc_count
        diversity_score = min(source_doc_count / 3, 1.0)

        # Entity coverage: named entities in answer that appear in chunks
        chunk_text = " ".join(c.get("content", "") for c in chunks)
        # Simple heuristic: capitalized multi-word sequences
        answer_entities = set(re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)+\b', answer))
        if answer_entities:
            covered = sum(1 for e in answer_entities if e in chunk_text)
            entity_coverage = covered / len(answer_entities)
        else:
            entity_coverage = 1.0

        composite = (
            retrieval_quality.quality_score * TRUST_WEIGHTS["retrieval_quality"] +
            citation_result.verification_score * TRUST_WEIGHTS["citation_verification"] +
            diversity_score * TRUST_WEIGHTS["source_diversity"] +
            entity_coverage * TRUST_WEIGHTS["entity_coverage"]
        )

        label = (
            "High"         if composite >= 0.80 else
            "Moderate"     if composite >= 0.60 else
            "Low"          if composite >= 0.40 else
            "Insufficient"
        )

        unverified = [f"[Doc {i}]" for i in citation_result.suspicious_indices]

        return TrustScore(
            score=round(composite, 3),
            label=label,
            retrieval_quality=retrieval_quality,
            citation_verification=citation_result,
            unverified_claims=unverified,
            refusal_triggered=False,
            refusal_reason=None,
        )


# ── Singleton instances ──────────────────────────────────────────────────────
_validator = RetrievalQualityValidator()
_scorer = TrustScorer()


def validate_retrieval(query: str, chunks: list[dict]) -> RetrievalQuality:
    return _validator.validate(query, chunks)


def compute_trust_score(
    query: str,
    answer: str,
    chunks: list[dict],
    retrieval_quality: RetrievalQuality,
) -> TrustScore:
    return _scorer.compute(query, answer, chunks, retrieval_quality)
