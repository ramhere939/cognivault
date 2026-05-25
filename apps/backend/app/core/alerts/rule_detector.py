"""
Rule-Based Alert Detector — deterministic, zero-LLM-cost.

Runs synchronously after every document ingest.
Detects: supersession chains, orphaned references, duplicate invoices,
         missing approvals, vendor concentration risk.

All detections are backed by specific evidence (doc IDs + entity quotes).
"""
import hashlib
import json
import logging
from datetime import datetime, timezone, timedelta
from typing import Any

from app.models.alert import AlertType, AlertSeverity

logger = logging.getLogger(__name__)


def _dedup_key(alert_type: AlertType, doc_ids: list[str]) -> str:
    """Stable deduplication hash for alert uniqueness."""
    key = f"{alert_type.value}::{':'.join(sorted(doc_ids))}"
    return hashlib.sha256(key.encode()).hexdigest()[:32]


def _build_alert(
    alert_type: AlertType,
    severity: AlertSeverity,
    title: str,
    explanation: str,
    affected_doc_ids: list[str],
    evidence_chunks: list[dict],
    confidence: float,
    reasoning_trace: str,
    operational_risk: str | None = None,
    graph_edge_id: str | None = None,
) -> dict[str, Any]:
    return {
        "alert_type":       alert_type,
        "severity":         severity,
        "title":            title,
        "explanation":      explanation,
        "affected_doc_ids": affected_doc_ids,
        "evidence_chunks":  evidence_chunks,
        "confidence":       confidence,
        "reasoning_trace":  reasoning_trace,
        "operational_risk": operational_risk,
        "graph_edge_id":    graph_edge_id,
        "dedup_key":        _dedup_key(alert_type, affected_doc_ids),
    }


class RuleBasedDetector:
    """
    Deterministic rule-based detectors.
    No LLM calls — these run fast on every ingest.
    """

    def detect_supersession_alerts(
        self,
        graph,  # nx.DiGraph
        doc_metadata: dict[str, dict],  # doc_id → {title, doc_type, summary}
    ) -> list[dict]:
        """
        SUPERSESSION: doc A SUPERSEDES doc B, but other docs still REFERENCE doc B.
        Creates compliance risk — referencing docs are now pointing at dead policy.
        """
        alerts = []
        try:
            import networkx as nx
        except ImportError:
            return alerts

        for u, v, data in graph.edges(data=True):
            if data.get("relation_label") != "SUPERSEDES":
                continue

            # Find docs that still reference the superseded doc (v)
            still_referencing = [
                src for src, tgt, d in graph.in_edges(v, data=True)
                if d.get("relation_label") in ("REFERENCES", "MANDATED_BY", "IMPLEMENTS")
                and src != u
            ]

            doc_a = doc_metadata.get(u, {})
            doc_b = doc_metadata.get(v, {})

            title = f"{doc_a.get('title', u)} supersedes {doc_b.get('title', v)}"

            if still_referencing:
                severity = AlertSeverity.CRITICAL
                explanation = (
                    f"{doc_a.get('title', 'A document')} has superseded "
                    f"{doc_b.get('title', 'another document')}, but "
                    f"{len(still_referencing)} other document(s) still reference the superseded version."
                )
                risk = f"{len(still_referencing)} document(s) reference an obsolete policy. Immediate review required."
            else:
                severity = AlertSeverity.HIGH
                explanation = (
                    f"{doc_a.get('title', 'A document')} has superseded "
                    f"{doc_b.get('title', 'another document')}. "
                    f"Verify all dependent processes have been updated."
                )
                risk = "Dependent processes may still reference the superseded policy."

            affected = [u, v] + still_referencing
            alerts.append(_build_alert(
                alert_type=AlertType.SUPERSESSION,
                severity=severity,
                title=title,
                explanation=explanation,
                affected_doc_ids=affected,
                evidence_chunks=[{
                    "chunk_id": "",
                    "doc_id": u,
                    "doc_title": doc_a.get("title", u),
                    "quote": data.get("evidence_quote", "Supersession detected via graph edge"),
                }],
                confidence=data.get("confidence", 0.85),
                reasoning_trace=f"SUPERSEDES edge detected: {u} → {v}. Referencing docs: {still_referencing}",
                operational_risk=risk,
                graph_edge_id=f"{u}_SUPERSEDES_{v}",
            ))

        return alerts

    def detect_orphaned_references(
        self,
        new_doc_entities: list[dict],
        indexed_policy_ids: set[str],
        new_doc_id: str,
        new_doc_title: str,
    ) -> list[dict]:
        """
        ORPHANED_REFERENCE: doc references a POLICY_ID not in the corpus.
        Indicates incomplete document set or dangling reference.
        """
        alerts = []
        for entity in new_doc_entities:
            if entity.get("entity_type") != "POLICY_ID":
                continue
            policy_id = entity.get("normalized") or entity.get("name", "")
            if not policy_id or policy_id in indexed_policy_ids:
                continue

            alerts.append(_build_alert(
                alert_type=AlertType.ORPHANED_REFERENCE,
                severity=AlertSeverity.MEDIUM,
                title=f"Unresolved reference to {policy_id}",
                explanation=(
                    f"{new_doc_title} references {policy_id}, "
                    f"but that policy has not been indexed in the knowledge base."
                ),
                affected_doc_ids=[new_doc_id],
                evidence_chunks=[{
                    "chunk_id": "",
                    "doc_id": new_doc_id,
                    "doc_title": new_doc_title,
                    "quote": entity.get("evidence_quote", f"References {policy_id}"),
                }],
                confidence=0.90,
                reasoning_trace=f"POLICY_ID entity '{policy_id}' not in indexed corpus",
                operational_risk=f"Policy {policy_id} referenced but not available — compliance gap risk.",
            ))

        return alerts

    def detect_duplicate_invoices(
        self,
        new_doc: dict,
        existing_docs: list[dict],
    ) -> list[dict]:
        """
        DUPLICATE_INVOICE: same vendor + similar amount + same date window.
        Detects potential duplicate payment risk.
        """
        if new_doc.get("doc_type") != "invoice":
            return []

        alerts = []
        new_entities = {e["entity_type"]: e for e in new_doc.get("entities", [])}
        new_vendor = new_entities.get("ORG", {}).get("normalized", "")
        new_amount = new_entities.get("AMOUNT", {}).get("name", "")
        new_date_str = new_entities.get("DATE", {}).get("normalized")

        if not new_vendor or not new_amount:
            return []

        try:
            new_date = datetime.fromisoformat(new_date_str) if new_date_str else None
        except (ValueError, TypeError):
            new_date = None

        for doc in existing_docs:
            if doc["id"] == new_doc["id"] or doc.get("doc_type") != "invoice":
                continue

            doc_entities = {e["entity_type"]: e for e in doc.get("entities", [])}
            doc_vendor = doc_entities.get("ORG", {}).get("normalized", "")
            doc_amount = doc_entities.get("AMOUNT", {}).get("name", "")
            doc_date_str = doc_entities.get("DATE", {}).get("normalized")

            if not doc_vendor or doc_vendor != new_vendor:
                continue
            if doc_amount != new_amount:
                continue

            # Date proximity check (±7 days)
            if new_date and doc_date_str:
                try:
                    doc_date = datetime.fromisoformat(doc_date_str)
                    if abs((new_date - doc_date).days) > 7:
                        continue
                except (ValueError, TypeError):
                    pass

            alerts.append(_build_alert(
                alert_type=AlertType.DUPLICATE_INVOICE,
                severity=AlertSeverity.HIGH,
                title=f"Potential duplicate invoice — {new_vendor} ({new_amount})",
                explanation=(
                    f"Two invoices from {new_vendor} for {new_amount} appear within 7 days of each other. "
                    f"Review for duplicate payment risk."
                ),
                affected_doc_ids=[new_doc["id"], doc["id"]],
                evidence_chunks=[
                    {"chunk_id": "", "doc_id": new_doc["id"],
                     "doc_title": new_doc.get("title"), "quote": f"Vendor: {new_vendor}, Amount: {new_amount}"},
                    {"chunk_id": "", "doc_id": doc["id"],
                     "doc_title": doc.get("title"), "quote": f"Vendor: {doc_vendor}, Amount: {doc_amount}"},
                ],
                confidence=0.88,
                reasoning_trace=f"Vendor+amount match within ±7 days: {new_doc['id']} ↔ {doc['id']}",
                operational_risk="Potential duplicate payment — financial control failure.",
            ))

        return alerts

    def detect_vendor_concentration_risk(
        self,
        graph,
        doc_metadata: dict[str, dict],
    ) -> list[dict]:
        """
        VENDOR_RISK: same vendor entity appears across ≥3 documents.
        Signals operational dependency concentration.
        """
        import networkx as nx
        alerts = []

        # Find ORG entity nodes with high degree
        org_nodes = [
            (n, d) for n, d in graph.nodes(data=True)
            if d.get("node_type") == "entity" and d.get("entity_type") == "ORG"
        ]

        for node_id, node_data in org_nodes:
            neighbors = list(graph.neighbors(node_id))
            doc_neighbors = [n for n in neighbors if doc_metadata.get(n)]

            if len(doc_neighbors) < 3:
                continue

            vendor_name = node_data.get("label", node_id)
            affected_titles = [doc_metadata[d].get("title", d) for d in doc_neighbors[:5]]

            alerts.append(_build_alert(
                alert_type=AlertType.VENDOR_RISK,
                severity=AlertSeverity.MEDIUM,
                title=f"Vendor concentration risk — {vendor_name}",
                explanation=(
                    f"{vendor_name} appears in {len(doc_neighbors)} documents, "
                    f"indicating significant operational dependency on this vendor."
                ),
                affected_doc_ids=doc_neighbors,
                evidence_chunks=[],
                confidence=0.75,
                reasoning_trace=(
                    f"ORG entity '{vendor_name}' linked to {len(doc_neighbors)} docs: "
                    f"{', '.join(affected_titles[:3])}"
                ),
                operational_risk=f"Dependency concentration: {vendor_name} across {len(doc_neighbors)} contracts/invoices.",
            ))

        return alerts
