from __future__ import annotations

import hashlib
import json
import os
import tempfile
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class ArtifactRecord:
    id: str
    path: str
    category: str
    content_type: str
    size_bytes: int
    sha256: str
    modified_at: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ArtifactCatalogResult:
    catalog_path: Path
    artifact_count: int
    total_size_bytes: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "catalog_path": str(self.catalog_path),
            "artifact_count": self.artifact_count,
            "total_size_bytes": self.total_size_bytes,
        }


class ArtifactManager:
    """Catalog, resolve and explicitly prune generated Portfolio OS artifacts."""

    GENERATED_ROOTS = (
        "analysis",
        "github",
        "portfolio",
        "history",
        "trends",
        "dashboard",
        "pipeline",
        "policy",
        "workspace",
        "backlog",
        "reuse",
        "lineage",
        "documents",
        "telemetry",
        "jobs",
    )

    def __init__(self, workspace: Path) -> None:
        self.workspace = workspace.expanduser().resolve()
        self.root = self.workspace / "artifacts"
        self.catalog_path = self.root / "catalog.json"

    def build_catalog(self) -> ArtifactCatalogResult:
        records: list[ArtifactRecord] = []
        for root_name in self.GENERATED_ROOTS:
            root = self.workspace / root_name
            if not root.exists():
                continue
            for path in sorted(root.rglob("*")):
                if not path.is_file() or path == self.catalog_path:
                    continue
                try:
                    raw = path.read_bytes()
                    stat = path.stat()
                except OSError:
                    continue
                relative = path.relative_to(self.workspace).as_posix()
                records.append(
                    ArtifactRecord(
                        id=hashlib.sha256(relative.encode("utf-8")).hexdigest()[:16],
                        path=relative,
                        category=root_name,
                        content_type=self._content_type(path),
                        size_bytes=len(raw),
                        sha256=hashlib.sha256(raw).hexdigest(),
                        modified_at=datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat(),
                    )
                )
        payload = {
            "schema_version": 1,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "workspace": str(self.workspace),
            "summary": {
                "artifact_count": len(records),
                "total_size_bytes": sum(item.size_bytes for item in records),
                "categories": self._category_counts(records),
            },
            "artifacts": [item.to_dict() for item in records],
        }
        self._write(self.catalog_path, payload)
        return ArtifactCatalogResult(
            self.catalog_path,
            len(records),
            sum(item.size_bytes for item in records),
        )

    def resolve(self, artifact_id: str) -> Path:
        catalog = self._load_catalog()
        for item in catalog.get("artifacts", []):
            if isinstance(item, dict) and item.get("id") == artifact_id:
                path = (self.workspace / str(item["path"])).resolve()
                if self.workspace not in path.parents:
                    raise ValueError("catalog artifact escapes workspace")
                if not path.is_file():
                    raise FileNotFoundError(str(path))
                return path
        raise KeyError(artifact_id)

    def retention_plan(self, *, keep_history: int = 30, keep_runs: int = 100) -> dict[str, Any]:
        candidates = []
        candidates.extend(self._older_than_limit(self.workspace / "history" / "snapshots", keep_history))
        candidates.extend(self._older_than_limit(self.workspace / "pipeline" / "runs", keep_runs))
        return {
            "schema_version": 1,
            "keep_history": keep_history,
            "keep_runs": keep_runs,
            "delete_count": len(candidates),
            "delete_bytes": sum(path.stat().st_size for path in candidates if path.exists()),
            "paths": [path.relative_to(self.workspace).as_posix() for path in candidates],
        }

    def apply_retention(self, plan: dict[str, Any], *, confirm: bool = False) -> dict[str, Any]:
        if not confirm:
            raise ValueError("retention requires confirm=True")
        deleted = []
        for relative in plan.get("paths", []):
            path = (self.workspace / str(relative)).resolve()
            if self.workspace not in path.parents or not path.is_file():
                continue
            path.unlink()
            deleted.append(str(relative))
        self.build_catalog()
        return {"deleted_count": len(deleted), "paths": deleted}

    def _load_catalog(self) -> dict[str, Any]:
        if not self.catalog_path.exists():
            self.build_catalog()
        payload = json.loads(self.catalog_path.read_text(encoding="utf-8"))
        return payload if isinstance(payload, dict) else {}

    @staticmethod
    def _content_type(path: Path) -> str:
        return {
            ".json": "application/json",
            ".md": "text/markdown",
            ".html": "text/html",
            ".txt": "text/plain",
        }.get(path.suffix.lower(), "application/octet-stream")

    @staticmethod
    def _category_counts(records: list[ArtifactRecord]) -> dict[str, int]:
        counts: dict[str, int] = {}
        for record in records:
            counts[record.category] = counts.get(record.category, 0) + 1
        return dict(sorted(counts.items()))

    @staticmethod
    def _older_than_limit(root: Path, keep: int) -> list[Path]:
        if not root.exists():
            return []
        files = sorted(
            (path for path in root.iterdir() if path.is_file()),
            key=lambda path: (path.stat().st_mtime, path.name),
            reverse=True,
        )
        return files[max(0, keep) :]

    @staticmethod
    def _write(path: Path, payload: dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
        temporary = Path(temporary_name)
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
                json.dump(payload, handle, indent=2, sort_keys=True)
                handle.write("\n")
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, path)
        finally:
            temporary.unlink(missing_ok=True)
