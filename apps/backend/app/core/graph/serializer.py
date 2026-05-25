"""
Graph serializer: NetworkX → React Flow format.
Computes layout positions using spring_layout.
"""
import math
import logging
from typing import Optional
import networkx as nx
from app.core.graph.builder import (
    get_graph, get_subgraph, get_graph_stats,
    EDGE_STYLES, NODE_COLORS
)
from app.schemas.graph import GraphNode, GraphEdge, GraphNodeData, GraphResponse

logger = logging.getLogger(__name__)

# MENTIONS edges clutter the graph — only show in subgraph/detail views
HIDE_IN_FULL_GRAPH = {"MENTIONS"}


_cached_positions: dict[str, dict] = {}
_cached_nodes: set[str] = set()


def _compute_positions(G: nx.DiGraph) -> dict[str, dict]:
    """Use spring layout with caching to avoid random jumps on re-render."""
    global _cached_positions, _cached_nodes
    
    if G.number_of_nodes() == 0:
        return {}

    current_nodes = set(G.nodes())
    
    # If the nodes are exactly the same, reuse the cached layout
    if current_nodes == _cached_nodes and _cached_positions:
        return {n: _cached_positions[n] for n in current_nodes if n in _cached_positions}

    # If there's a huge change or cache is empty, compute from scratch
    if not _cached_positions or len(current_nodes - _cached_nodes) > len(current_nodes) / 2:
        if G.number_of_nodes() < 3:
            raw = nx.spring_layout(G, seed=42, scale=500)
        else:
            raw = nx.spring_layout(G, seed=42, scale=800, k=2.0)
            
        _cached_positions = {node: {"x": round(x, 2), "y": round(y, 2)} for node, (x, y) in raw.items()}
        _cached_nodes = current_nodes
        return _cached_positions

    # Incremental update: fix existing nodes, lay out new ones
    pos_init = {}
    fixed_nodes = []
    
    for n in _cached_nodes.intersection(current_nodes):
        p = _cached_positions[n]
        pos_init[n] = (p["x"], p["y"])
        fixed_nodes.append(n)
        
    for n in current_nodes - _cached_nodes:
        pos_init[n] = (0.0, 0.0)

    # Use fixed nodes to anchor the graph layout
    raw = nx.spring_layout(G, pos=pos_init, fixed=fixed_nodes, seed=42, scale=800, k=2.0)
    
    _cached_positions = {node: {"x": round(x, 2), "y": round(y, 2)} for node, (x, y) in raw.items()}
    _cached_nodes = current_nodes
    return _cached_positions


def serialize_graph(
    G: Optional[nx.DiGraph] = None,
    focus_doc_id: Optional[str] = None,
    hide_mentions: bool = True,
) -> GraphResponse:
    """Convert NetworkX graph to React Flow format."""
    if G is None:
        G = get_graph()

    positions = _compute_positions(G)
    nodes = []
    edges = []

    for node_id, data in G.nodes(data=True):
        node_type = data.get("node_type", "KEYWORD")
        
        # If we are hiding MENTIONS edges, the entity nodes will be disconnected floating dots.
        # Hide them to keep the Global View clean (only showing Documents).
        if hide_mentions and node_type != "DOCUMENT":
            continue

        color = NODE_COLORS.get(node_type, "#6B7280")

        nodes.append(GraphNode(
            id=node_id,
            type="knowledgeNode",
            data=GraphNodeData(
                label=data.get("label", node_id[:12]),
                nodeType=node_type,
                docType=data.get("doc_type"),
                department=data.get("department"),
                date=data.get("date"),
                summary=data.get("summary"),
                status=data.get("status"),
                isHighlighted=node_id == focus_doc_id,
                metadata={
                    "color": color,
                    "confidence": data.get("confidence", 1.0),
                },
            ),
            position=positions.get(node_id, {"x": 0.0, "y": 0.0}),
        ))

    for source, target, data in G.edges(data=True):
        label = data.get("relation_label", "RELATES_TO")
        if hide_mentions and label in HIDE_IN_FULL_GRAPH:
            continue

        style_config = EDGE_STYLES.get(label, EDGE_STYLES["RELATES_TO"])
        edges.append(GraphEdge(
            id=f"{source}--{target}--{label}",
            source=source,
            target=target,
            type="smoothstep",
            animated=style_config["animated"],
            label=label,
            data={
                "relation_label": label,
                "confidence": data.get("confidence", 0.8),
                "evidence_quote": data.get("evidence_quote", ""),
                "explanation": data.get("explanation", ""),
            },
            style={
                "stroke": style_config["color"],
                "strokeWidth": style_config["width"],
            },
        ))

    stats = get_graph_stats()
    return GraphResponse(nodes=nodes, edges=edges, stats=stats)


def serialize_subgraph(doc_id: str, depth: int = 2) -> GraphResponse:
    """Get React Flow format subgraph centered on a document."""
    subG = get_subgraph(doc_id, depth=depth)
    return serialize_graph(G=subG, focus_doc_id=doc_id, hide_mentions=False)

def serialize_impact_graph(doc_id: str) -> GraphResponse:
    """Get React Flow format impact graph for a document."""
    from app.core.graph.builder import get_impact_graph
    subG = get_impact_graph(doc_id)
    return serialize_graph(G=subG, focus_doc_id=doc_id, hide_mentions=False)

def serialize_dependency_graph(doc_id: str) -> GraphResponse:
    """Get React Flow format dependency graph for a document."""
    from app.core.graph.builder import get_dependency_graph
    subG = get_dependency_graph(doc_id)
    return serialize_graph(G=subG, focus_doc_id=doc_id, hide_mentions=False)
