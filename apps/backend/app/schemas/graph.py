from typing import Optional, Any
from pydantic import BaseModel


class GraphNodeData(BaseModel):
    label: str
    nodeType: str           # DOCUMENT | PERSON | ORG | POLICY_ID | AMOUNT | REGULATION
    docType: Optional[str] = None
    department: Optional[str] = None
    date: Optional[str] = None
    summary: Optional[str] = None
    status: Optional[str] = None
    isHighlighted: bool = False
    metadata: dict = {}


class GraphNode(BaseModel):
    id: str
    type: str = "knowledgeNode"
    data: GraphNodeData
    position: dict[str, float]


class GraphEdge(BaseModel):
    id: str
    source: str
    target: str
    type: str = "smoothstep"
    animated: bool = False
    label: Optional[str] = None
    data: dict = {}
    style: dict = {}


class GraphResponse(BaseModel):
    nodes: list[GraphNode]
    edges: list[GraphEdge]
    stats: dict[str, Any] = {}


class RelationshipResponse(BaseModel):
    id: str
    source_id: str
    source_type: str
    target_id: str
    target_type: str
    relation_label: str
    confidence: Optional[float] = None
    evidence_quote: Optional[str] = None
    explanation: Optional[str] = None

    model_config = {"from_attributes": True}
