from __future__ import annotations

import json
import os
import re
import tempfile
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from portfolio_os.sync import load_state


@dataclass(frozen=True)
class LineageEdge:
    source: str
    target: str | None
    relation: str
    evidence: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class LineageResult:
    json_path: Path
    markdown_path: Path
    edge_count: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "json_path": str(self.json_path),
            "markdown_path": str(self.markdown_path),
            "edge_count": self.edge_count,
        }


class RepositoryLineage:
    """Build explicit repository merge, archive, reference and supersession relationships."""

    def __init__(self, workspace: Path, config_path: Path | None = None) -> None:
        self.workspace = workspace.expanduser().resolve()
        self.config_path = (config_path or Path("config/portfolio.json")).expanduser().resolve()
        self.output_dir = self.workspace / "lineage"
        self.json_path = self.output_dir / "repository-lineage.json"
        self.markdown_path = self.output_dir / "repository-lineage.md"

    def build(self) -> LineageResult:
        config = self._load_config()
        state = load_state(self.workspace / "sync-state.json")
        known = {item.name.lower(): item.full_name for item in state.repositories.values()}
        owner = state.owner or str(config.get("owner") or "")
        edges: list[LineageEdge] = []
        for repository in config.get("repositories", []):
            if not isinstance(repository, dict):
                continue
            name = str(repository.get("name") or "")
            classification = str(repository.get("classification") or "")
            action = str(repository.get("next_action") or "")
            if not name:
                continue
            source = known.get(name.lower(), f"{owner}/{name}" if owner else name)
            target = self._target(classification, action, owner, known)
            relation = self._relation(classification, action)
            if relation:
                edges.append(LineageEdge(source, target, relation, action or classification))
        edges.sort(key=lambda item: (item.source.lower(), item.relation, item.target or ""))
        payload = {
            "schema_version": 1,
            "summary": {
                "edge_count": len(edges),
                "merge_count": sum(item.relation == "merge_into" for item in edges),
                "archive_candidate_count": sum(item.relation == "archive_candidate" for item in edges),
                "reference_count": sum(item.relation == "reference_of" for item in edges),
                "migration_count": sum(item.relation == "migration_source_for" for item in edges),
            },
            "edges": [item.to_dict() for item in edges],
            "impact": self._impact(edges),
        }
        self._write(self.json_path, json.dumps(payload, indent=2, sort_keys=True) + "\n")
        self._write(self.markdown_path, self._render(payload))
        return LineageResult(self.json_path, self.markdown_path, len(edges))

    def _load_config(self) -> dict[str, Any]:
        if not self.config_path.exists():
            return {}
        payload = json.loads(self.config_path.read_text(encoding="utf-8"))
        return payload if isinstance(payload, dict) else {}

    @staticmethod
    def _relation(classification: str, action: str) -> str | None:
        lowered = classification.lower()
        if lowered.startswith("merge-into-"):
            return "merge_into"
        if lowered == "migration-source":
            return "migration_source_for"
        if "archive-candidate" in lowered:
            return "archive_candidate"
        if "reference-fork" in lowered:
            return "reference_of"
        if "consolidate" in lowered:
            return "consolidate_with"
        if "supersed" in action.lower():
            return "superseded_by"
        return None

    @staticmethod
    def _target(
        classification: str,
        action: str,
        owner: str,
        known: dict[str, str],
    ) -> str | None:
        lowered = classification.lower()
        if lowered.startswith("merge-into-"):
            raw = classification[len("merge-into-") :]
            return known.get(raw.lower(), f"{owner}/{raw}" if owner else raw)
        candidates = re.findall(r"\b[A-Za-z0-9_.-]+\b", action)
        for candidate in candidates:
            if candidate.lower() in known:
                return known[candidate.lower()]
        return None

    @staticmethod
    def _impact(edges: list[LineageEdge]) -> dict[str, Any]:
        inbound: dict[str, list[dict[str, str]]] = {}
        outbound: dict[str, list[dict[str, str | None]]] = {}
        for edge in edges:
            outbound.setdefault(edge.source, []).append({"relation": edge.relation, "target": edge.target})
            if edge.target:
                inbound.setdefault(edge.target, []).append({"relation": edge.relation, "source": edge.source})
        return {
            "inbound": {key: value for key, value in sorted(inbound.items())},
            "outbound": {key: value for key, value in sorted(outbound.items())},
        }

    @staticmethod
    def _render(payload: dict[str, Any]) -> str:
        lines = ["# Repository Lineage", ""]
        for edge in payload["edges"]:
            target = f" → `{edge['target']}`" if edge.get("target") else ""
            lines.append(f"- `{edge['source']}` — **{edge['relation']}**{target}: {edge['evidence']}")
        if not payload["edges"]:
            lines.append("No explicit lineage relationships were found.")
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
