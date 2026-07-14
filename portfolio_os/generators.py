from __future__ import annotations

import json
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class GeneratedDocuments:
    changelog_path: Path
    release_notes_path: Path
    architecture_path: Path

    def to_dict(self) -> dict[str, str]:
        return {
            "changelog_path": str(self.changelog_path),
            "release_notes_path": str(self.release_notes_path),
            "architecture_path": str(self.architecture_path),
        }


class PortfolioDocumentGenerator:
    """Generate deterministic portfolio documentation from persisted evidence."""

    def __init__(self, workspace: Path) -> None:
        self.workspace = workspace.expanduser().resolve()
        self.summary_path = self.workspace / "portfolio" / "portfolio-summary.json"
        self.delta_path = self.workspace / "history" / "latest-delta.json"
        self.graph_path = self.workspace / "portfolio" / "portfolio-graph.json"
        self.output_dir = self.workspace / "documents"

    def build(self) -> GeneratedDocuments:
        summary = self._load(self.summary_path)
        delta = self._load(self.delta_path)
        graph = self._load(self.graph_path)
        changelog_path = self.output_dir / "CHANGELOG.generated.md"
        release_notes_path = self.output_dir / "RELEASE-NOTES.generated.md"
        architecture_path = self.output_dir / "ARCHITECTURE.generated.md"
        self._write(changelog_path, self._changelog(summary, delta))
        self._write(release_notes_path, self._release_notes(summary, delta))
        self._write(architecture_path, self._architecture(summary, graph))
        return GeneratedDocuments(changelog_path, release_notes_path, architecture_path)

    @staticmethod
    def _load(path: Path) -> dict[str, Any]:
        if not path.exists():
            return {}
        payload = json.loads(path.read_text(encoding="utf-8"))
        return payload if isinstance(payload, dict) else {}

    @staticmethod
    def _changelog(summary: dict[str, Any], delta: dict[str, Any]) -> str:
        repositories = summary.get("repositories", [])
        delta_summary = delta.get("summary", {})
        lines = ["# Generated Portfolio Changelog", "", "## Latest refresh", ""]
        for key in ("repositories_added", "repositories_removed", "repositories_changed", "regressions"):
            if key in delta_summary:
                lines.append(f"- {key.replace('_', ' ').title()}: **{delta_summary[key]}**")
        if len(lines) == 4:
            lines.append("- No structured delta evidence is available.")
        lines.extend(["", "## Repository state", ""])
        for repository in repositories:
            if not isinstance(repository, dict):
                continue
            lines.append(
                f"- `{repository.get('full_name', 'unknown')}` — "
                f"status: {repository.get('sync_status', 'unknown')}; "
                f"HEAD: `{repository.get('head_sha') or 'unknown'}`; "
                f"findings: {repository.get('finding_count', 0)}"
            )
        return "\n".join(lines).rstrip() + "\n"

    @staticmethod
    def _release_notes(summary: dict[str, Any], delta: dict[str, Any]) -> str:
        overview = summary.get("summary", {})
        intelligence = summary.get("intelligence", {}).get("averages", {})
        delta_summary = delta.get("summary", {})
        lines = [
            "# Generated Portfolio Release Notes",
            "",
            "## Portfolio health",
            "",
            f"- Active repositories: **{overview.get('active_count', 0)}**",
            f"- Analysis coverage: **{float(overview.get('analysis_coverage', 0)):.1%}**",
            f"- Intelligence score: **{float(overview.get('intelligence_score', 0)):.1f}/100**",
            f"- Findings: **{overview.get('total_findings', 0)}**",
            "",
            "## Intelligence",
            "",
        ]
        lines.extend(
            f"- {name.replace('_', ' ').title()}: **{float(value):.1f}/100**"
            for name, value in intelligence.items()
        )
        lines.extend(["", "## Changes since previous snapshot", ""])
        if delta_summary:
            lines.extend(f"- {key.replace('_', ' ').title()}: **{value}**" for key, value in delta_summary.items())
        else:
            lines.append("- No previous snapshot delta is available.")
        return "\n".join(lines).rstrip() + "\n"

    @staticmethod
    def _architecture(summary: dict[str, Any], graph: dict[str, Any]) -> str:
        repositories = summary.get("repositories", [])
        graph_summary = graph.get("summary", {})
        lines = [
            "# Generated Portfolio Architecture",
            "",
            "This document is generated only from persisted repository analysis and knowledge-graph evidence.",
            "",
            "## Portfolio graph",
            "",
            f"- Nodes: **{graph_summary.get('node_count', 0)}**",
            f"- Edges: **{graph_summary.get('edge_count', 0)}**",
            "",
            "## Repository architecture",
            "",
        ]
        for repository in repositories:
            if not isinstance(repository, dict):
                continue
            frameworks = repository.get("frameworks", []) or []
            lines.extend(
                [
                    f"### {repository.get('full_name', 'unknown')}",
                    "",
                    f"- Primary language: **{repository.get('primary_language') or 'unknown'}**",
                    f"- Frameworks: **{', '.join(frameworks) if frameworks else 'none detected'}**",
                    f"- Files analyzed: **{repository.get('file_count', 0)}**",
                    f"- Architecture score: **{repository.get('intelligence', {}).get('scores', {}).get('architecture', {}).get('score', 0)}/100**",
                    "",
                ]
            )
        return "\n".join(lines).rstrip() + "\n"

    @staticmethod
    def _write(path: Path, content: str) -> None:
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
