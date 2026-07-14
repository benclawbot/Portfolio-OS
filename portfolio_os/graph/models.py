from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Literal

NodeType = Literal["repository", "component", "technology", "capability", "workflow", "release"]
RelationType = Literal[
    "depends-on",
    "consumes",
    "duplicates",
    "supersedes",
    "extracted-from",
    "contains",
    "uses",
    "implements",
    "related-to",
]


@dataclass(frozen=True)
class GraphNode:
    id: str
    type: NodeType
    label: str
    properties: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class GraphEdge:
    source: str
    target: str
    relation: RelationType
    confidence: float = 1.0
    evidence: tuple[str, ...] = ()
    properties: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence must be between 0 and 1")


@dataclass
class KnowledgeGraph:
    schema_version: str = "1.0"
    nodes: dict[str, GraphNode] = field(default_factory=dict)
    edges: list[GraphEdge] = field(default_factory=list)

    def add_node(self, node: GraphNode) -> None:
        existing = self.nodes.get(node.id)
        if existing and existing != node:
            merged = dict(existing.properties)
            merged.update(node.properties)
            self.nodes[node.id] = GraphNode(node.id, node.type, node.label, merged)
        else:
            self.nodes[node.id] = node

    def add_edge(self, edge: GraphEdge) -> None:
        if edge.source not in self.nodes or edge.target not in self.nodes:
            raise KeyError("edge endpoints must exist before adding the edge")
        key = (edge.source, edge.target, edge.relation)
        for index, existing in enumerate(self.edges):
            if (existing.source, existing.target, existing.relation) == key:
                if edge.confidence > existing.confidence:
                    self.edges[index] = edge
                return
        self.edges.append(edge)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "nodes": [asdict(self.nodes[key]) for key in sorted(self.nodes)],
            "edges": [
                asdict(edge)
                for edge in sorted(self.edges, key=lambda item: (item.source, item.relation, item.target))
            ],
            "summary": {"node_count": len(self.nodes), "edge_count": len(self.edges)},
        }
