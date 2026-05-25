"""
Alert Engine — orchestrates all detectors and persists to SQLite.

Execution order (synchronous, fast):
  1. RuleBasedDetector   — O(entities), deterministic
  2. GraphAnomalyDetector — O(E), NetworkX traversal
  3. Alert deduplication  — skip if dedup_key already exists
  4. Persist to DB

SemanticAlertDetector (LLM-based) runs asynchronously as background task.
"""
import asyncio
import logging
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text

from app.models.alert import Alert, AlertType, AlertSeverity
from app.core.alerts.rule_detector import RuleBasedDetector
from app.core.alerts.graph_detector import GraphAnomalyDetector

logger = logging.getLogger(__name__)

_rule_detector = RuleBasedDetector()
_graph_detector = GraphAnomalyDetector()


async def run_alert_pipeline(
    db: AsyncSession,
    graph,               # nx.DiGraph
    new_doc: dict,       # newly indexed document metadata
    new_doc_entities: list[dict],
    all_docs: list[dict],
    doc_metadata: dict,  # doc_id → metadata dict
) -> list[dict]:
    """
    Run all detectors and persist new alerts.
    Returns list of newly created alert dicts.
    """
    raw_alerts: list[dict] = []

    # ── Get indexed policy IDs for orphan detection ───────────────────────────
    indexed_policy_ids = _get_indexed_policy_ids(all_docs)
    indexed_doc_ids = {d["id"] for d in all_docs}

    # ── 1. Rule-based detectors ───────────────────────────────────────────────
    try:
        raw_alerts += _rule_detector.detect_supersession_alerts(graph, doc_metadata)
        raw_alerts += _rule_detector.detect_orphaned_references(
            new_doc_entities, indexed_policy_ids,
            new_doc["id"], new_doc.get("title", new_doc.get("filename", ""))
        )
        raw_alerts += _rule_detector.detect_duplicate_invoices(new_doc, all_docs)
        raw_alerts += _rule_detector.detect_vendor_concentration_risk(graph, doc_metadata)
    except Exception as e:
        logger.error(f"Rule detector error: {e}", exc_info=True)

    # ── 2. Graph anomaly detectors ────────────────────────────────────────────
    try:
        raw_alerts += _graph_detector.detect_circular_dependencies(graph, doc_metadata)
        raw_alerts += _graph_detector.detect_approval_chain_breaks(graph, doc_metadata, indexed_doc_ids)
        raw_alerts += _graph_detector.detect_compliance_gaps(graph, doc_metadata)
        raw_alerts += _graph_detector.detect_revocation_gaps(graph, doc_metadata)
    except Exception as e:
        logger.error(f"Graph anomaly detector error: {e}", exc_info=True)

    logger.info(f"Alert pipeline generated {len(raw_alerts)} candidate alerts for doc {new_doc['id']}")

    # ── 3. Dedup + persist ────────────────────────────────────────────────────
    persisted = await _persist_alerts(db, raw_alerts)
    logger.info(f"Persisted {len(persisted)} new alerts (deduplicated)")

    return persisted


async def _persist_alerts(db: AsyncSession, raw_alerts: list[dict]) -> list[dict]:
    """Persist alerts, skipping any with existing dedup_key."""
    persisted = []

    for alert_data in raw_alerts:
        dedup_key = alert_data.get("dedup_key", "")
        if not dedup_key:
            continue

        # Check if alert already exists
        existing = await db.execute(
            select(Alert).where(Alert.dedup_key == dedup_key)
        )
        if existing.scalar_one_or_none():
            logger.debug(f"Alert deduped: {dedup_key[:8]}...")
            continue

        alert = Alert(
            alert_type=alert_data["alert_type"],
            severity=alert_data["severity"],
            title=alert_data["title"],
            explanation=alert_data["explanation"],
            reasoning_trace=alert_data.get("reasoning_trace"),
            dedup_key=dedup_key,
            affected_doc_ids=alert_data.get("affected_doc_ids", []),
            evidence_chunks=alert_data.get("evidence_chunks", []),
            graph_edge_id=alert_data.get("graph_edge_id"),
            confidence=alert_data.get("confidence", 0.0),
            operational_risk=alert_data.get("operational_risk"),
        )
        db.add(alert)
        persisted.append(alert_data)

    await db.commit()
    return persisted


def _get_indexed_policy_ids(all_docs: list[dict]) -> set[str]:
    """Extract all POLICY_ID entity values from indexed documents."""
    policy_ids = set()
    for doc in all_docs:
        for entity in doc.get("entities", []):
            if entity.get("entity_type") == "POLICY_ID":
                name = entity.get("normalized") or entity.get("name", "")
                if name:
                    policy_ids.add(name)
    return policy_ids


async def get_alerts_summary(db: AsyncSession) -> dict:
    """Dashboard summary counts."""
    result = await db.execute(text("""
        SELECT
            COUNT(*) as total,
            COALESCE(SUM(CASE WHEN resolved = 0 THEN 1 ELSE 0 END), 0) as unresolved,
            COALESCE(SUM(CASE WHEN severity = 'CRITICAL' AND resolved = 0 THEN 1 ELSE 0 END), 0) as critical
        FROM alerts
    """))
    row = result.fetchone()

    by_severity = await db.execute(text("""
        SELECT severity, COUNT(*) as cnt FROM alerts WHERE resolved = 0 GROUP BY severity
    """))
    by_type = await db.execute(text("""
        SELECT alert_type, COUNT(*) as cnt FROM alerts WHERE resolved = 0 GROUP BY alert_type
    """))

    return {
        "total": row.total if row else 0,
        "unresolved": row.unresolved if row else 0,
        "critical_count": row.critical if row else 0,
        "by_severity": {r.severity: r.cnt for r in by_severity},
        "by_type": {r.alert_type: r.cnt for r in by_type},
    }
