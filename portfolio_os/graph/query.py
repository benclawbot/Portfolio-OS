from __future__ import annotations

from collections import deque

from .models import GraphEdge, KnowledgeGraph


class GraphQuery:
    def __init__(self, graph: KnowledgeGraph) -> None:
        self.graph = graph

    def neighbors(self, node_id: str, relation: str | None = None, incoming: bool = False) -> list[GraphEdge]:
        edges = [edge for edge in self.graph.edges if (edge.target if incoming else edge.source) == node_id]
        if relation:
            edges = [edge for edge in edges if edge.relation == relation]
        return sorted(edges, key=lambda edge: (edge.relation, edge.target, edge.source))

    def impact(self, node_id: str, max_depth: int = 5) -> dict:
        visited = {node_id}
        queue = deque([(node_id, 0)])
        affected: list[dict] = []
        while queue:
            current, depth = queue.popleft()
            if depth >= max_depth:
                continue
            for edge in self.neighbors(current, incoming=True):
                dependent = edge.source
                if dependent in visited:
                    continue
                visited.add(dependent)
                affected.append({"node": dependent, "depth": depth + 1, "via": edge.relation})
                queue.append((dependent, depth + 1))
        return {"root": node_id, "affected": affected, "count": len(affected)}

    def path(self, source: str, target: str, max_depth: int = 8) -> list[dict]:
        queue = deque([(source, [])])
        visited = {source}
        while queue:
            current, route = queue.popleft()
            if len(route) >= max_depth:
                continue
            for edge in self.neighbors(current):
                step = {"source": edge.source, "relation": edge.relation, "target": edge.target}
                if edge.target == target:
                    return route + [step]
                if edge.target not in visited:
                    visited.add(edge.target)
                    queue.append((edge.target, route + [step]))
        return []
