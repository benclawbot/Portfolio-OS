from __future__ import annotations

import hashlib
import json
import os
import tempfile
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from portfolio_os.sync import load_state


_SOURCE_SUFFIXES = {
    ".py", ".js", ".jsx", ".ts", ".tsx", ".rs", ".go", ".java", ".kt", ".kts",
    ".swift", ".c", ".h", ".cpp", ".hpp", ".cs", ".rb", ".php", ".sh", ".ps1",
}
_EXCLUDED_PARTS = {
    ".git", "node_modules", "vendor", "dist", "build", "target", ".venv", "venv",
    "coverage", ".pytest_cache", ".mypy_cache", ".ruff_cache", "__pycache__",
}


@dataclass(frozen=True)
class DuplicateOccurrence:
    repository: str
    path: str
    size_bytes: int


@dataclass(frozen=True)
class DuplicateGroup:
    hash: str
    occurrences: tuple[DuplicateOccurrence, ...]
    line_count: int
    recommendation: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "hash": self.hash,
            "occurrences": [asdict(item) for item in self.occurrences],
            "line_count": self.line_count,
            "recommendation": self.recommendation,
        }


@dataclass(frozen=True)
class ReuseResult:
    json_path: Path
    markdown_path: Path
    duplicate_group_count: int
    shared_library_recommendation_count: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "json_path": str(self.json_path),
            "markdown_path": str(self.markdown_path),
            "duplicate_group_count": self.duplicate_group_count,
            "shared_library_recommendation_count": self.shared_library_recommendation_count,
        }


class PortfolioReuseAnalyzer:
    """Find exact cross-repository source duplication with reproducible file hashes."""

    def __init__(self, workspace: Path, *, minimum_bytes: int = 120, minimum_lines: int = 5) -> None:
        self.workspace = workspace.expanduser().resolve()
        self.minimum_bytes = minimum_bytes
        self.minimum_lines = minimum_lines
        self.output_dir = self.workspace / "reuse"
        self.json_path = self.output_dir / "duplicate-components.json"
        self.markdown_path = self.output_dir / "shared-library-recommendations.md"

    def build(self) -> ReuseResult:
        state = load_state(self.workspace / "sync-state.json")
        by_hash: dict[str, list[DuplicateOccurrence]] = {}
        line_counts: dict[str, int] = {}
        for repository_id in sorted(state.repositories):
            repository = state.repositories[repository_id]
            root = Path(repository.path)
            if not repository.accessible or repository.archived or not root.is_dir():
                continue
            for path in self._source_files(root):
                try:
                    raw = path.read_bytes()
                except OSError:
                    continue
                if len(raw) < self.minimum_bytes:
                    continue
                normalized = raw.replace(b"\r\n", b"\n").strip()
                lines = normalized.count(b"\n") + 1
                if lines < self.minimum_lines:
                    continue
                digest = hashlib.sha256(normalized).hexdigest()
                relative = path.relative_to(root).as_posix()
                by_hash.setdefault(digest, []).append(
                    DuplicateOccurrence(repository.full_name, relative, len(raw))
                )
                line_counts[digest] = lines

        groups: list[DuplicateGroup] = []
        for digest, occurrences in by_hash.items():
            repositories = {item.repository for item in occurrences}
            if len(repositories) < 2:
                continue
            sorted_occurrences = tuple(sorted(occurrences, key=lambda item: (item.repository, item.path)))
            names = {Path(item.path).name for item in sorted_occurrences}
            recommendation = (
                f"Extract `{next(iter(names))}` into a shared library used by {len(repositories)} repositories."
                if len(names) == 1
                else f"Consolidate this {line_counts[digest]}-line component into a shared library or template."
            )
            groups.append(DuplicateGroup(digest, sorted_occurrences, line_counts[digest], recommendation))
        groups.sort(key=lambda item: (-item.line_count, item.hash))

        payload = {
            "schema_version": 1,
            "summary": {
                "duplicate_group_count": len(groups),
                "duplicate_file_count": sum(len(group.occurrences) for group in groups),
                "shared_library_recommendation_count": len(groups),
            },
            "groups": [group.to_dict() for group in groups],
        }
        self._write(self.json_path, json.dumps(payload, indent=2, sort_keys=True) + "\n")
        self._write(self.markdown_path, self._render(groups))
        return ReuseResult(self.json_path, self.markdown_path, len(groups), len(groups))

    @staticmethod
    def _source_files(root: Path) -> list[Path]:
        files = []
        for path in root.rglob("*"):
            if not path.is_file() or path.suffix.lower() not in _SOURCE_SUFFIXES:
                continue
            try:
                relative_parts = path.relative_to(root).parts
            except ValueError:
                continue
            if any(part in _EXCLUDED_PARTS for part in relative_parts):
                continue
            files.append(path)
        return sorted(files)

    @staticmethod
    def _render(groups: list[DuplicateGroup]) -> str:
        lines = ["# Shared Library Recommendations", ""]
        if not groups:
            lines.append("No exact cross-repository source duplication was detected.")
            return "\n".join(lines) + "\n"
        for index, group in enumerate(groups, start=1):
            lines.extend(
                [
                    f"## {index}. Duplicate component — {group.line_count} lines",
                    "",
                    f"- SHA-256: `{group.hash}`",
                    f"- Recommendation: {group.recommendation}",
                    "- Occurrences:",
                ]
            )
            lines.extend(f"  - `{item.repository}:{item.path}`" for item in group.occurrences)
            lines.append("")
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
