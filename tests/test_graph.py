from pathlib import Path

from portfolio_os.graph import GraphBuilder, GraphEdge, GraphNode, GraphQuery, GraphStore, KnowledgeGraph


def test_graph_rejects_missing_edge_endpoints() -> None:
    graph = KnowledgeGraph()
    graph.add_node(GraphNode("repo:a", "repository", "a"))
    try:
        graph.add_edge(GraphEdge("repo:a", "repo:b", "depends-on"))
    except KeyError:
        pass
    else:
        raise AssertionError("missing endpoint should fail")


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


def test_decision_relationship_creates_declared_nodes() -> None:
    graph = KnowledgeGraph()
    GraphBuilder().add_decision_relationship(graph, "Zeus", "Medusa", "supersedes", "confirmed decision")
    assert "repo:Zeus" in graph.nodes
    assert graph.edges[0].relation == "supersedes"
    assert graph.edges[0].properties["source"] == "decision"
