from __future__ import annotations

from pathlib import Path
from typing import cast

from portfolio_os.dna import DNABuilder, SimilarityEngine
from portfolio_os.engine import AnalysisEngine

from .models import GraphEdge, GraphNode, KnowledgeGraph, RelationType


class GraphBuilder:
    def __init__(self) -> None:
        self.analysis_engine = AnalysisEngine()
        self.dna_builder = DNABuilder()
        self.similarity_engine = SimilarityEngine()

    def add_repository(self, graph: KnowledgeGraph, root: Path) -> str:
        root = root.expanduser().resolve()
        analysis = self.analysis_engine.analyze(root)
        if analysis.errors:
            raise RuntimeError(f"analysis failed for {root}: {analysis.errors}")
        dna = self.dna_builder.build(analysis)
        repository_id = f"repo:{root.name}"
        graph.add_node(
            GraphNode(
                repository_id,
                "repository",
                root.name,
                {
                    "root": str(root),
                    "fingerprint": dna.fingerprint,
                    "primary_language": analysis.facts.get("languages", {}).get("primary"),
                    "file_count": analysis.facts.get("repository", {}).get("file_count", 0),
                },
            )
        )
        for dimension_name, values in dna.features.to_dict().items():
            for value in values:
                node_type = "capability" if dimension_name == "capabilities" else "technology"
                node_id = f"{node_type}:{dimension_name}:{value}"
                graph.add_node(GraphNode(node_id, node_type, value, {"dimension": dimension_name}))
                relation: RelationType = "implements" if node_type == "capability" else "uses"
                graph.add_edge(GraphEdge(repository_id, node_id, relation, 1.0, (f"DNA:{dimension_name}",)))
        return repository_id

    def infer_repository_relationships(self, graph: KnowledgeGraph, threshold: float = 0.55) -> None:
        repositories = [node for node in graph.nodes.values() if node.type == "repository"]
        for index, left in enumerate(repositories):
            for right in repositories[index + 1 :]:
                left_root = Path(str(left.properties["root"]))
                right_root = Path(str(right.properties["root"]))
                left_dna = self.dna_builder.build(self.analysis_engine.analyze(left_root))
                right_dna = self.dna_builder.build(self.analysis_engine.analyze(right_root))
                comparison = self.similarity_engine.compare(left_dna, right_dna)
                if comparison.score < threshold:
                    continue
                relation: RelationType = "duplicates" if comparison.score >= 0.85 else "related-to"
                evidence = tuple(comparison.reasons[:5])
                dimension_scores = {dimension.name: dimension.score for dimension in comparison.dimensions}
                graph.add_edge(
                    GraphEdge(
                        left.id,
                        right.id,
                        relation,
                        comparison.score,
                        evidence,
                        {"dimension_scores": dimension_scores},
                    )
                )

    def add_decision_relationship(
        self,
        graph: KnowledgeGraph,
        source: str,
        target: str,
        relation: str,
        evidence: str,
    ) -> None:
        source_id = source if source.startswith("repo:") else f"repo:{source}"
        target_id = target if target.startswith("repo:") else f"repo:{target}"
        for node_id, label in ((source_id, source.removeprefix("repo:")), (target_id, target.removeprefix("repo:"))):
            if node_id not in graph.nodes:
                graph.add_node(GraphNode(node_id, "repository", label, {"declared_only": True}))
        graph.add_edge(
            GraphEdge(
                source_id,
                target_id,
                cast(RelationType, relation),
                1.0,
                (evidence,),
                {"source": "decision"},
            )
        )
