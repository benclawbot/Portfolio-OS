from __future__ import annotations

import json
import os
import tempfile
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from portfolio_os.graph import GraphBuilder, GraphStore, KnowledgeGraph
from portfolio_os.intelligence import RepositoryIntelligence
from portfolio_os.sync import RepositoryState, load_state


@dataclass(frozen=True)
class PortfolioBuildResult:
    summary_path: Path
    report_path: Path
    graph_path: Path
    data: dict[str, Any]


class PortfolioBuilder:
    """Build deterministic portfolio artifacts from a synchronized workspace."""

    def __init__(self, workspace: Path, output_dir: Path | None = None) -> None:
        self.workspace = workspace.expanduser().resolve()
        self.output_dir = (output_dir or self.workspace / "portfolio").expanduser().resolve()
        self.state_path = self.workspace / "sync-state.json"
        self.analysis_dir = self.workspace / "analysis"
        self.github_dir = self.workspace / "github" / "repositories"
        self.intelligence = RepositoryIntelligence()

    def build(self, similarity_threshold: float = 0.55) -> PortfolioBuildResult:
        state = load_state(self.state_path)
        repositories = [state.repositories[key] for key in sorted(state.repositories)]
        records = [self._repository_record(repository) for repository in repositories]
        data = self._aggregate(state.owner, state.synchronized_at, records)

        self.output_dir.mkdir(parents=True, exist_ok=True)
        summary_path = self.output_dir / "portfolio-summary.json"
        report_path = self.output_dir / "portfolio-report.md"
        graph_path = self.output_dir / "portfolio-graph.json"
        self._write_json_atomic(summary_path, data)
        self._write_text_atomic(report_path, self._render_markdown(data))
        self._build_graph(repositories, graph_path, similarity_threshold)
        return PortfolioBuildResult(summary_path, report_path, graph_path, data)

    def _repository_record(self, repository: RepositoryState) -> dict[str, Any]:
        analysis, analysis_error = self._load_optional_json(self.analysis_dir / f"{repository.id}.json")
        github, github_error = self._load_optional_json(self.github_dir / f"{repository.id}.json")
        facts = analysis.get("facts", {}) if analysis else {}
        summary = analysis.get("summary", {}) if analysis else {}
        findings = analysis.get("findings", []) if analysis else []
        record = {
            "id": repository.id,
            "name": repository.name,
            "full_name": repository.full_name,
            "path": repository.path,
            "default_branch": repository.default_branch,
            "head_sha": repository.head_sha,
            "visibility": repository.visibility,
            "fork": repository.fork,
            "archived": repository.archived,
            "accessible": repository.accessible,
            "dirty": repository.dirty,
            "sync_status": repository.status,
            "updated_at": repository.updated_at,
            "analysis_available": analysis is not None,
            "analysis_error": analysis_error,
            "github_index_available": github is not None,
            "github_index_error": github_error,
            "primary_language": facts.get("languages", {}).get("primary"),
            "frameworks": sorted(facts.get("frameworks", {}).get("detected", [])),
            "file_count": facts.get("repository", {}).get("file_count", 0),
            "test_file_count": facts.get("quality", {}).get("test_file_count", 0),
            "finding_count": summary.get("finding_count", len(findings)),
            "error_count": summary.get("error_count", 0),
            "severity_counts": dict(Counter(item.get("severity", "unknown") for item in findings)),
        }
        record["intelligence"] = self.intelligence.evaluate(record, analysis, github)
        return record

    @staticmethod
    def _load_optional_json(path: Path) -> tuple[dict[str, Any] | None, str | None]:
        if not path.exists():
            return None, None
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            return None, str(error)
        if not isinstance(payload, dict):
            return None, "JSON root must be an object"
        return payload, None

    def _aggregate(self, owner: str, synchronized_at: str, repositories: list[dict[str, Any]]) -> dict[str, Any]:
        languages = Counter(item["primary_language"] for item in repositories if item["primary_language"])
        frameworks = Counter(framework for item in repositories for framework in item["frameworks"])
        severities = Counter()
        for item in repositories:
            severities.update(item["severity_counts"])
        active = [item for item in repositories if item["accessible"] and not item["archived"]]
        analyzed = [item for item in repositories if item["analysis_available"]]
        score_names = ("architecture", "technical_debt", "security", "release_readiness")
        score_averages = {
            name: round(
                sum(item["intelligence"]["scores"][name]["score"] for item in active) / len(active),
                1,
            )
            if active
            else 0.0
            for name in score_names
        }
        return {
            "schema_version": 2,
            "owner": owner,
            "source_synchronized_at": synchronized_at,
            "summary": {
                "repository_count": len(repositories),
                "active_count": len(active),
                "archived_count": sum(item["archived"] for item in repositories),
                "inaccessible_count": sum(not item["accessible"] for item in repositories),
                "dirty_count": sum(item["dirty"] for item in repositories),
                "analyzed_count": len(analyzed),
                "analysis_coverage": round(len(analyzed) / len(repositories), 4) if repositories else 0.0,
                "github_indexed_count": sum(item["github_index_available"] for item in repositories),
                "total_files": sum(item["file_count"] for item in analyzed),
                "total_test_files": sum(item["test_file_count"] for item in analyzed),
                "total_findings": sum(item["finding_count"] for item in analyzed),
                "analysis_errors": sum(item["error_count"] for item in analyzed),
                "intelligence_score": round(
                    sum(item["intelligence"]["overall_score"] for item in active) / len(active),
                    1,
                )
                if active
                else 0.0,
            },
            "intelligence": {"averages": score_averages},
            "languages": dict(languages.most_common()),
            "frameworks": dict(frameworks.most_common()),
            "finding_severities": dict(severities.most_common()),
            "attention": {
                "dirty": [item["full_name"] for item in repositories if item["dirty"]],
                "inaccessible": [item["full_name"] for item in repositories if not item["accessible"]],
                "archived": [item["full_name"] for item in repositories if item["archived"]],
                "missing_analysis": [item["full_name"] for item in active if not item["analysis_available"]],
                "missing_github_index": [item["full_name"] for item in active if not item["github_index_available"]],
                "analysis_errors": [item["full_name"] for item in analyzed if item["error_count"]],
                "low_release_readiness": [
                    item["full_name"]
                    for item in active
                    if item["intelligence"]["scores"]["release_readiness"]["score"] < 60
                ],
            },
            "repositories": repositories,
        }

    def _build_graph(self, repositories: list[RepositoryState], graph_path: Path, threshold: float) -> None:
        graph = KnowledgeGraph()
        builder = GraphBuilder()
        eligible = [
            repository
            for repository in repositories
            if repository.accessible
            and not repository.archived
            and not repository.dirty
            and Path(repository.path).is_dir()
            and (Path(repository.path) / ".git").exists()
        ]
        for repository in eligible:
            builder.add_repository(graph, Path(repository.path))
        builder.infer_repository_relationships(graph, threshold)
        GraphStore().save(graph, graph_path)

    @staticmethod
    def _write_json_atomic(path: Path, data: dict[str, Any]) -> None:
        PortfolioBuilder._write_text_atomic(path, json.dumps(data, indent=2, sort_keys=True) + "\n")

    @staticmethod
    def _write_text_atomic(path: Path, content: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
        temporary = Path(temporary_name)
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
                handle.write(content)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, path)
        finally:
            temporary.unlink(missing_ok=True)

    @staticmethod
    def _render_markdown(data: dict[str, Any]) -> str:
        summary = data["summary"]
        lines = [
            "# Portfolio Report",
            "",
            f"Owner: `{data['owner'] or 'unknown'}`  ",
            f"Source synchronization: `{data['source_synchronized_at'] or 'not synchronized'}`",
            "",
            "## Overview",
            "",
            f"- Repositories: **{summary['repository_count']}**",
            f"- Active: **{summary['active_count']}**",
            f"- Archived: **{summary['archived_count']}**",
            f"- Inaccessible: **{summary['inaccessible_count']}**",
            f"- Dirty working trees: **{summary['dirty_count']}**",
            f"- Analysis coverage: **{summary['analysis_coverage']:.1%}**",
            f"- GitHub metadata indexed: **{summary['github_indexed_count']}**",
            f"- Portfolio intelligence score: **{summary['intelligence_score']:.1f}/100**",
            f"- Files analyzed: **{summary['total_files']}**",
            f"- Test files detected: **{summary['total_test_files']}**",
            f"- Findings: **{summary['total_findings']}**",
            "",
            "## Intelligence",
            "",
        ]
        lines.extend(
            f"- {name.replace('_', ' ').title()}: **{score:.1f}/100**"
            for name, score in data["intelligence"]["averages"].items()
        )
        lines.extend(["", "## Languages", ""])
        lines.extend(f"- {name}: {count}" for name, count in data["languages"].items())
        if not data["languages"]:
            lines.append("- No analyzed language evidence yet.")
        lines.extend(["", "## Attention", ""])
        for category, values in data["attention"].items():
            lines.append(f"### {category.replace('_', ' ').title()}")
            lines.extend(f"- `{value}`" for value in values)
            if not values:
                lines.append("- None")
            lines.append("")
        lines.extend(["## Repositories", ""])
        for repository in data["repositories"]:
            language = repository["primary_language"] or "unknown"
            intelligence = repository["intelligence"]["overall_score"]
            lines.append(
                f"- `{repository['full_name']}` — {repository['sync_status']}; "
                f"language: {language}; findings: {repository['finding_count']}; intelligence: {intelligence}/100"
            )
        return "\n".join(lines).rstrip() + "\n"
