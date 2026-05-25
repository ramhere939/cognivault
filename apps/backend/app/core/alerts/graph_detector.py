"""
Graph Anomaly Detector — NetworkX traversal-based alerts.

Detects: circular dependencies, broken approval chains, compliance gaps.
Runs after every graph rebuild. No LLM calls.
"""
import logging
import networkx as nx

from app.models.alert import AlertType, AlertSeverity
from app.core.alerts.rule_detector import _build_alert, _dedup_key

logger = logging.getLogger(__name__)

# Edge types that form operational dependency chains
OPERATIONAL_EDGES = {"ENABLES", "MANDATED_BY", "BLOCKS", "IMPLEMENTS"}
SUPERSESSION_EDGES = {"SUPERSEDES", "REVOKES", "AMENDS"}


class GraphAnomalyDetector:
    """
    NetworkX graph traversal-based anomaly detection.
    All algorithms are O(V+E) or better — negligible cost up to 10k edges.
    """

    def detect_circular_dependencies(
        self,
        graph: nx.DiGraph,
        doc_metadata: dict,
    ) -> list[dict]:
        """
        CIRCULAR_DEPENDENCY: A ENABLES B ENABLES A (deadlock).
        Filtered to operational edges only — avoids false positives from
        bidirectional reference chains which are normal.
        """
        alerts = []

        # Build operational-edges-only subgraph
        op_edges = [
            (u, v) for u, v, d in graph.edges(data=True)
            if d.get("relation_label") in OPERATIONAL_EDGES
        ]
        if not op_edges:
            return []

        op_graph = nx.DiGraph()
        op_graph.add_edges_from(op_edges)

        try:
            cycles = list(nx.simple_cycles(op_graph))
        except nx.NetworkXError:
            return []

        for cycle in cycles:
            if len(cycle) < 2:
                continue
            doc_titles = [doc_metadata.get(n, {}).get("title", n) for n in cycle]
            cycle_str = " → ".join(doc_titles[:4])

            alerts.append(_build_alert(
                alert_type=AlertType.CIRCULAR_DEPENDENCY,
                severity=AlertSeverity.CRITICAL,
                title=f"Circular dependency detected ({len(cycle)} documents)",
                explanation=(
                    f"A circular operational dependency was detected: {cycle_str}. "
                    f"This creates a logical deadlock that may block all involved processes."
                ),
                affected_doc_ids=cycle,
                evidence_chunks=[],
                confidence=1.0,  # Graph cycles are deterministic
                reasoning_trace=f"nx.simple_cycles detected: {cycle}",
                operational_risk="Circular dependency creates an unresolvable prerequisite chain.",
            ))

        return alerts

    def detect_approval_chain_breaks(
        self,
        graph: nx.DiGraph,
        doc_metadata: dict,
        indexed_doc_ids: set[str],
    ) -> list[dict]:
        """
        MISSING_APPROVAL: Doc has MANDATED_BY or ENABLES edge pointing to a
        document that either isn't indexed or has status != 'indexed'.
        """
        alerts = []

        for u, v, data in graph.edges(data=True):
            if data.get("relation_label") not in ("MANDATED_BY", "ENABLES"):
                continue

            doc_u = doc_metadata.get(u, {})

            # If the prerequisite (v) is not in our indexed set
            if v not in indexed_doc_ids:
                alerts.append(_build_alert(
                    alert_type=AlertType.MISSING_APPROVAL,
                    severity=AlertSeverity.HIGH,
                    title=f"Missing prerequisite for {doc_u.get('title', u)}",
                    explanation=(
                        f"{doc_u.get('title', u)} has a {data['relation_label']} dependency "
                        f"on a document that is not indexed in the knowledge base."
                    ),
                    affected_doc_ids=[u],
                    evidence_chunks=[{
                        "chunk_id": "",
                        "doc_id": u,
                        "doc_title": doc_u.get("title", u),
                        "quote": data.get("evidence_quote", "Dependency detected via graph edge"),
                    }],
                    confidence=0.80,
                    reasoning_trace=f"{data['relation_label']} edge to {v} — target not in indexed corpus",
                    operational_risk=f"Prerequisite document not available — {doc_u.get('title', u)} may not be executable.",
                ))

        return alerts

    def detect_compliance_gaps(
        self,
        graph: nx.DiGraph,
        doc_metadata: dict,
    ) -> list[dict]:
        """
        COMPLIANCE_GAP: A policy/regulation exists (doc type=policy/circular)
        but has no IMPLEMENTS or PROCURES_UNDER edges pointing to it.
        Indicates regulation exists but nothing operationalizes it.
        """
        alerts = []

        policy_nodes = [
            n for n, d in graph.nodes(data=True)
            if doc_metadata.get(n, {}).get("doc_type") in ("policy", "circular", "scheme")
        ]

        for policy_id in policy_nodes:
            # Check if anything implements this policy
            implementing_edges = [
                (u, v, d) for u, v, d in graph.in_edges(policy_id, data=True)
                if d.get("relation_label") in ("IMPLEMENTS", "PROCURES_UNDER", "MANDATED_BY")
            ]

            if not implementing_edges:
                doc = doc_metadata.get(policy_id, {})
                # Only alert if policy has been indexed (not a phantom reference)
                if not doc:
                    continue

                alerts.append(_build_alert(
                    alert_type=AlertType.COMPLIANCE_GAP,
                    severity=AlertSeverity.MEDIUM,
                    title=f"No implementation evidence — {doc.get('title', policy_id)}",
                    explanation=(
                        f"{doc.get('title', 'A policy')} is in the knowledge base "
                        f"but no document implementing or procuring under it has been indexed."
                    ),
                    affected_doc_ids=[policy_id],
                    evidence_chunks=[],
                    confidence=0.70,
                    reasoning_trace=f"Policy node {policy_id} has no inbound IMPLEMENTS/PROCURES_UNDER edges",
                    operational_risk="Policy may be unenforced or implementation documents are missing.",
                ))

        return alerts

    def detect_revocation_gaps(
        self,
        graph: nx.DiGraph,
        doc_metadata: dict,
    ) -> list[dict]:
        """
        COMPLIANCE_GAP (revocation): A REVOKES B, but nothing replaces B.
        Creates a regulatory vacuum.
        """
        alerts = []

        for u, v, data in graph.edges(data=True):
            if data.get("relation_label") != "REVOKES":
                continue

            # Check if anything supersedes or amends v (i.e., provides replacement)
            replacement_edges = [
                d for _, tgt, d in graph.in_edges(v, data=True)
                if d.get("relation_label") in ("SUPERSEDES", "AMENDS") and tgt == v
            ]

            if not replacement_edges:
                doc_u = doc_metadata.get(u, {})
                doc_v = doc_metadata.get(v, {})

                alerts.append(_build_alert(
                    alert_type=AlertType.COMPLIANCE_GAP,
                    severity=AlertSeverity.HIGH,
                    title=f"Regulatory vacuum — {doc_v.get('title', v)} revoked with no replacement",
                    explanation=(
                        f"{doc_u.get('title', u)} revokes {doc_v.get('title', v)} "
                        f"but no replacement policy has been indexed. "
                        f"This creates a regulatory gap."
                    ),
                    affected_doc_ids=[u, v],
                    evidence_chunks=[{
                        "chunk_id": "",
                        "doc_id": u,
                        "doc_title": doc_u.get("title", u),
                        "quote": data.get("evidence_quote", "REVOKES edge detected"),
                    }],
                    confidence=0.85,
                    reasoning_trace=f"REVOKES edge {u} → {v} with no SUPERSEDES replacement",
                    operational_risk=f"No replacement for revoked {doc_v.get('title', v)} — compliance vacuum.",
                ))

        return alerts
