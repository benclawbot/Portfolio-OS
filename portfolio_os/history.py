from __future__ import annotations

import hashlib
import json
import os
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class SnapshotResult:
    snapshot_path: Path
    latest_path: Path
    delta_path: Path
    delta: dict[str, Any]


class PortfolioHistory:
    """Persist immutable portfolio snapshots and compute deterministic deltas."""

    def __init__(self, workspace: Path) -> None:
        self.workspace = workspace.expanduser().resolve()
        self.history_dir = self.workspace / "history"
        self.latest_path = self.history_dir / "latest.json"
        self.delta_path = self.history_dir / "latest-delta.json"

    def record(self, data: dict[str, Any], recorded_at: str | None = None) -> SnapshotResult:
        timestamp = recorded_at or datetime.now(timezone.utc).isoformat()
        previous = self.load_latest()
        canonical = json.dumps(data, sort_keys=True, separators=(",", ":"))
        fingerprint = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
        snapshot = {
            "schema_version": 1,
            "recorded_at": timestamp,
            "fingerprint": fingerprint,
            "portfolio": data,
        }
        safe_timestamp = timestamp.replace(":", "-")
        snapshot_path = self.history_dir / "snapshots" / f"{safe_timestamp}-{fingerprint[:12]}.json"
        delta = self.compare(previous.get("portfolio") if previous else None, data)
        self._write_json_atomic(snapshot_path, snapshot)
        self._write_json_atomic(self.latest_path, snapshot)
        self._write_json_atomic(self.delta_path, delta)
        return SnapshotResult(snapshot_path, self.latest_path, self.delta_path, delta)

    def load_latest(self) -> dict[str, Any] | None:
        if not self.latest_path.exists():
            return None
        return json.loads(self.latest_path.read_text(encoding="utf-8"))

    @staticmethod
    def compare(previous: dict[str, Any] | None, current: dict[str, Any]) -> dict[str, Any]:
        current_repositories = {item["id"]: item for item in current.get("repositories", [])}
        previous_repositories = {
            item["id"]: item for item in (previous or {}).get("repositories", [])
        }
        added_ids = sorted(set(current_repositories) - set(previous_repositories))
        removed_ids = sorted(set(previous_repositories) - set(current_repositories))
        common_ids = sorted(set(current_repositories) & set(previous_repositories))
        changed = []
        for repository_id in common_ids:
            before = previous_repositories[repository_id]
            after = current_repositories[repository_id]
            fields = {}
            for field in (
                "name",
                "full_name",
                "head_sha",
                "visibility",
                "archived",
                "accessible",
                "dirty",
                "primary_language",
                "file_count",
                "test_file_count",
                "finding_count",
                "error_count",
            ):
                if before.get(field) != after.get(field):
                    fields[field] = {"before": before.get(field), "after": after.get(field)}
            if fields:
                changed.append({"id": repository_id, "full_name": after.get("full_name"), "fields": fields})

        previous_summary = (previous or {}).get("summary", {})
        current_summary = current.get("summary", {})
        summary_delta = {}
        for key in sorted(set(previous_summary) | set(current_summary)):
            before = previous_summary.get(key)
            after = current_summary.get(key)
            if isinstance(before, (int, float)) and isinstance(after, (int, float)):
                summary_delta[key] = {"before": before, "after": after, "change": after - before}
            elif before != after:
                summary_delta[key] = {"before": before, "after": after}

        return {
            "schema_version": 1,
            "baseline": previous is None,
            "summary": {
                "added_count": len(added_ids),
                "removed_count": len(removed_ids),
                "changed_count": len(changed),
            },
            "added": [current_repositories[item] for item in added_ids],
            "removed": [previous_repositories[item] for item in removed_ids],
            "changed": changed,
            "summary_delta": summary_delta,
        }

    @staticmethod
    def _write_json_atomic(path: Path, data: dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
        temporary = Path(temporary_name)
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
                json.dump(data, handle, indent=2, sort_keys=True)
                handle.write("\n")
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, path)
        finally:
            temporary.unlink(missing_ok=True)
