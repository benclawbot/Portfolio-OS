from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

from .models import GraphEdge, GraphNode, KnowledgeGraph


class GraphStore:
    def load(self, path: Path) -> KnowledgeGraph:
        if not path.exists():
            return KnowledgeGraph()
        data = json.loads(path.read_text(encoding="utf-8"))
        graph = KnowledgeGraph(schema_version=str(data.get("schema_version", "1.0")))
        for raw in data.get("nodes", []):
            graph.add_node(GraphNode(raw["id"], raw["type"], raw["label"], raw.get("properties", {})))
        for raw in data.get("edges", []):
            graph.add_edge(
                GraphEdge(
                    raw["source"],
                    raw["target"],
                    raw["relation"],
                    float(raw.get("confidence", 1.0)),
                    tuple(raw.get("evidence", [])),
                    raw.get("properties", {}),
                )
            )
        return graph

    def save(self, graph: KnowledgeGraph, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = json.dumps(graph.to_dict(), indent=2, sort_keys=False) + "\n"
        descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent, text=True)
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
                handle.write(payload)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary_name, path)
        finally:
            temporary = Path(temporary_name)
            if temporary.exists():
                temporary.unlink()
