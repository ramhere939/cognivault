"""
NetworkX-based knowledge graph builder.
Constructs and persists the document-entity relationship graph.
"""
import json
import logging
from pathlib import Path
from typing import Optional
import networkx as nx

logger = logging.getLogger(__name__)

# Edge color mapping — used by serializer for React Flow
EDGE_STYLES = {
    "SUPERSEDES":     {"color": "#F97316", "width": 3, "animated": True},
    "REVOKES":        {"color": "#DC2626", "width": 3, "animated": True},
    "AMENDS":         {"color": "#EAB308", "width": 2, "animated": False},
    "ENABLES":        {"color": "#10B981", "width": 2, "animated": False},
    "MANDATED_BY":    {"color": "#3B82F6", "width": 2, "animated": False},
    "BLOCKS":         {"color": "#EF4444", "width": 3, "animated": True},
    "IMPLEMENTS":     {"color": "#22C55E", "width": 2, "animated": False},
    "PROCURES_UNDER": {"color": "#6366F1", "width": 2, "animated": False},
    "REFERENCES":     {"color": "#94A3B8", "width": 1, "animated": False},
    "DUPLICATES":     {"color": "#F43F5E", "width": 2, "animated": True},
    "MENTIONS":       {"color": "#CBD5E1", "width": 1, "animated": False},
    "RELATES_TO":     {"color": "#94A3B8", "width": 1, "animated": False},
}

NODE_COLORS = {
    "DOCUMENT":     "#4F46E5",
    "PERSON":       "#059669",
    "ORG":          "#D97706",
    "POLICY_ID":    "#DC2626",
    "AMOUNT":       "#7C3AED",
    "DATE":         "#0891B2",
    "REGULATION":   "#0E7490",
    "LOCATION":     "#65A30D",
    "KEYWORD":      "#6B7280",
}

_graph: Optional[nx.DiGraph] = None
_graphs_path: Optional[str] = None
GRAPH_FILE = "knowledge_graph.json"


def init_graph(graphs_path: str):
    global _graph, _graphs_path
    _graphs_path = graphs_path
    Path(graphs_path).mkdir(parents=True, exist_ok=True)
    _graph = _load_graph()
    logger.info(f"Graph initialized: {_graph.number_of_nodes()} nodes, {_graph.number_of_edges()} edges")


def _load_graph() -> nx.DiGraph:
    graph_file = Path(_graphs_path) / GRAPH_FILE
    if graph_file.exists():
        try:
            with open(graph_file, "r") as f:
                data = json.load(f)
            G = nx.node_link_graph(data, directed=True, multigraph=False)
            return G
        except Exception as e:
            logger.warning(f"Could not load existing graph: {e}. Starting fresh.")
    return nx.DiGraph()


def _save_graph():
    graph_file = Path(_graphs_path) / GRAPH_FILE
    data = nx.node_link_data(_graph)
    with open(graph_file, "w") as f:
        json.dump(data, f)


def get_graph() -> nx.DiGraph:
    if _graph is None:
        raise RuntimeError("Graph not initialized")
    return _graph


def add_document_node(doc_id: str, doc_data: dict):
    """Add or update a document node."""
    _graph.add_node(
        doc_id,
        node_type="DOCUMENT",
        label=doc_data.get("title") or doc_data.get("filename", doc_id[:8]),
        doc_type=doc_data.get("doc_type", "unknown"),
        department=doc_data.get("department", ""),
        date=doc_data.get("doc_date", ""),
        summary=doc_data.get("summary", ""),
        status=doc_data.get("status", "indexed"),
    )
    _save_graph()


def add_entity_node(entity_id: str, entity_data: dict):
    """Add or update an entity node."""
    _graph.add_node(
        entity_id,
        node_type=entity_data.get("entity_type", "KEYWORD"),
        label=entity_data.get("normalized") or entity_data.get("name", entity_id[:8]),
        doc_id=entity_data.get("doc_id", ""),
        confidence=entity_data.get("confidence", 0.8),
    )


def add_document_entity_edge(doc_id: str, entity_id: str, entity_name: str):
    """Connect a document to an entity it contains."""
    _graph.add_edge(
        doc_id,
        entity_id,
        relation_label="MENTIONS",
        confidence=0.99,
        evidence_quote=entity_name,
    )
    _save_graph()


def add_relationship_edge(
    source_id: str,
    target_id: str,
    relation_label: str,
    confidence: float,
    evidence_quote: str = "",
    explanation: str = "",
):
    """Add a cross-document relationship edge."""
    # Remove any existing edge between these nodes (keep highest confidence)
    if _graph.has_edge(source_id, target_id):
        existing = _graph[source_id][target_id]
        if existing.get("confidence", 0) >= confidence:
            return  # keep higher confidence edge

    _graph.add_edge(
        source_id,
        target_id,
        relation_label=relation_label,
        confidence=confidence,
        evidence_quote=evidence_quote,
        explanation=explanation,
    )
    _save_graph()
    logger.info(f"Graph edge: {source_id[:8]} --[{relation_label}]--> {target_id[:8]} (conf={confidence:.2f})")


def remove_document(doc_id: str):
    """Remove a document and all its edges from the graph. Also removes orphaned entities."""
    if _graph.has_node(doc_id):
        _graph.remove_node(doc_id)
        
        # Clean up orphaned entity nodes (degree 0)
        orphans = [n for n, d in _graph.degree() if d == 0 and _graph.nodes[n].get("node_type") != "DOCUMENT"]
        for orphan in orphans:
            _graph.remove_node(orphan)
            
        _save_graph()


def get_subgraph(doc_id: str, depth: int = 2) -> nx.DiGraph:
    """Get ego graph (subgraph centered on a document)."""
    if not _graph.has_node(doc_id):
        return nx.DiGraph()
    return nx.ego_graph(_graph, doc_id, radius=depth, undirected=True)


def get_impact_graph(doc_id: str) -> nx.DiGraph:
    """Get subgraph of documents impacted by this one (forward traversal of operational edges)."""
    if not _graph.has_node(doc_id):
        return nx.DiGraph()
    
    impact_G = nx.DiGraph()
    for u, v, d in _graph.edges(data=True):
        label = d.get("relation_label")
        if label in {"ENABLES", "BLOCKS", "SUPERSEDES", "REVOKES", "AMENDS"}:
            impact_G.add_edge(u, v)
        elif label in {"MANDATED_BY", "IMPLEMENTS", "PROCURES_UNDER"}:
            impact_G.add_edge(v, u)
            
    if not impact_G.has_node(doc_id):
        return nx.ego_graph(_graph, doc_id, radius=1)
        
    impacted_nodes = nx.descendants(impact_G, doc_id)
    impacted_nodes.add(doc_id)
    return _graph.subgraph(impacted_nodes).copy()


def get_dependency_graph(doc_id: str) -> nx.DiGraph:
    """Get subgraph of documents this one depends on (backward traversal of operational edges)."""
    if not _graph.has_node(doc_id):
        return nx.DiGraph()
        
    dep_G = nx.DiGraph()
    for u, v, d in _graph.edges(data=True):
        label = d.get("relation_label")
        if label in {"ENABLES", "BLOCKS", "SUPERSEDES", "REVOKES", "AMENDS"}:
            dep_G.add_edge(v, u)
        elif label in {"MANDATED_BY", "IMPLEMENTS", "PROCURES_UNDER"}:
            dep_G.add_edge(u, v) 
            
    if not dep_G.has_node(doc_id):
        return nx.ego_graph(_graph, doc_id, radius=1)
        
    dep_nodes = nx.descendants(dep_G, doc_id)
    dep_nodes.add(doc_id)
    return _graph.subgraph(dep_nodes).copy()


def get_graph_stats() -> dict:
    G = _graph
    doc_nodes = [n for n, d in G.nodes(data=True) if d.get("node_type") == "DOCUMENT"]
    return {
        "total_nodes": G.number_of_nodes(),
        "total_edges": G.number_of_edges(),
        "document_count": len(doc_nodes),
        "entity_count": G.number_of_nodes() - len(doc_nodes),
        "relationship_types": _count_relationship_types(),
    }


def _count_relationship_types() -> dict:
    counts = {}
    for _, _, data in _graph.edges(data=True):
        label = data.get("relation_label", "UNKNOWN")
        counts[label] = counts.get(label, 0) + 1
    return counts
