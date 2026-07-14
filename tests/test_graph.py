import shutil
from pathlib import Path

import pytest

from portfolio_os.graph import GraphBuilder, GraphEdge, GraphNode, GraphQuery, GraphStore, KnowledgeGraph


def test_graph_rejects_missing_edge_endpoints() -> None:
    graph = KnowledgeGraph()
    graph.add_node(GraphNode("repo:a", "repository", "a"))
    with pytest.raises(KeyError):
        graph.add_edge(GraphEdge("repo:a", "repo:b", "depends-on"))


def test_graph_rejects_invalid_confidence() -> None:
    with pytest.raises(ValueError, match="confidence"):
        GraphEdge("repo:a", "repo:b", "depends-on", 1.1)


def test_graph_merges_node_properties_and_keeps_stronger_edge() -> None:
    graph = KnowledgeGraph()
    graph.add_node(GraphNode("repo:a", "repository", "a", {"language": "Python"}))
    graph.add_node(GraphNode("repo:a", "repository", "a", {"files": 10}))
    graph.add_node(GraphNode("repo:b", "repository", "b"))
    graph.add_edge(GraphEdge("repo:a", "repo:b", "depends-on", 0.4, ("weak",)))
    graph.add_edge(GraphEdge("repo:a", "repo:b", "depends-on", 0.9, ("strong",)))

    assert graph.nodes["repo:a"].properties == {"language": "Python", "files": 10}
    assert len(graph.edges) == 1
    assert graph.edges[0].confidence == 0.9
    assert graph.edges[0].evidence == ("strong",)


def test_graph_store_round_trip(tmp_path: Path) -> None:
    graph = KnowledgeGraph()
    graph.add_node(GraphNode("repo:a", "repository", "a"))
    graph.add_node(GraphNode("repo:b", "repository", "b"))
    graph.add_edge(GraphEdge("repo:a", "repo:b", "depends-on", 0.9, ("fixture",)))
    path = tmp_path / "graph.json"
    GraphStore().save(graph, path)
    loaded = GraphStore().load(path)
    assert loaded.to_dict() == graph.to_dict()


def test_impact_traverses_reverse_dependencies() -> None:
    graph = KnowledgeGraph()
    for name in ("core", "desktop", "plugin"):
        graph.add_node(GraphNode(f"repo:{name}", "repository", name))
    graph.add_edge(GraphEdge("repo:desktop", "repo:core", "depends-on"))
    graph.add_edge(GraphEdge("repo:plugin", "repo:desktop", "depends-on"))
    result = GraphQuery(graph).impact("repo:core")
    assert [item["node"] for item in result["affected"]] == ["repo:desktop", "repo:plugin"]
    assert result["count"] == 2


def test_neighbors_filter_incoming_and_path_depth() -> None:
    graph = KnowledgeGraph()
    for name in ("a", "b", "c", "d"):
        graph.add_node(GraphNode(f"repo:{name}", "repository", name))
    graph.add_edge(GraphEdge("repo:a", "repo:b", "depends-on"))
    graph.add_edge(GraphEdge("repo:b", "repo:c", "uses"))
    graph.add_edge(GraphEdge("repo:d", "repo:b", "related-to"))
    query = GraphQuery(graph)

    assert [edge.source for edge in query.neighbors("repo:b", incoming=True)] == ["repo:a", "repo:d"]
    assert [edge.target for edge in query.neighbors("repo:b", relation="uses")] == ["repo:c"]
    assert query.path("repo:a", "repo:c") == [
        {"source": "repo:a", "relation": "depends-on", "target": "repo:b"},
        {"source": "repo:b", "relation": "uses", "target": "repo:c"},
    ]
    assert query.path("repo:a", "repo:c", max_depth=1) == []
    assert query.path("repo:c", "repo:a") == []


def test_decision_relationship_creates_declared_nodes() -> None:
    graph = KnowledgeGraph()
    GraphBuilder().add_decision_relationship(graph, "Zeus", "Medusa", "supersedes", "confirmed decision")
    assert "repo:Zeus" in graph.nodes
    assert graph.edges[0].relation == "supersedes"
    assert graph.edges[0].properties["source"] == "decision"


def test_builder_adds_repository_evidence_and_similarity(tmp_path: Path) -> None:
    fixture = Path(__file__).parent / "fixtures" / "sample_repo"
    left = tmp_path / "left"
    right = tmp_path / "right"
    shutil.copytree(fixture, left)
    shutil.copytree(fixture, right)

    graph = KnowledgeGraph()
    builder = GraphBuilder()
    left_id = builder.add_repository(graph, left)
    right_id = builder.add_repository(graph, right)
    builder.infer_repository_relationships(graph, threshold=0.5)

    assert left_id == "repo:left"
    assert right_id == "repo:right"
    assert graph.nodes[left_id].properties["file_count"] > 0
    assert any(edge.source == left_id and edge.relation in {"uses", "implements"} for edge in graph.edges)
    relationship = next(edge for edge in graph.edges if edge.source == left_id and edge.target == right_id)
    assert relationship.relation == "duplicates"
    assert relationship.confidence >= 0.85
    assert relationship.properties["dimension_scores"]
