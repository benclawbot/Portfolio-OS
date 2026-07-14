from __future__ import annotations

import json
import os
import tempfile
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class LockStatus:
    exists: bool
    path: Path
    pid: int | None
    started_at_epoch: float | None
    age_seconds: float | None
    stale: bool
    malformed: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "exists": self.exists,
            "path": str(self.path),
            "pid": self.pid,
            "started_at_epoch": self.started_at_epoch,
            "age_seconds": self.age_seconds,
            "stale": self.stale,
            "malformed": self.malformed,
        }


class RefreshOperations:
    """Persist refresh history and inspect workspace lock state."""

    def __init__(self, workspace: Path) -> None:
        self.workspace = workspace.expanduser().resolve()
        self.pipeline_dir = self.workspace / "pipeline"
        self.runs_dir = self.pipeline_dir / "runs"
        self.latest_path = self.pipeline_dir / "latest-run.json"
        self.lock_path = self.workspace / ".portfolio-os-refresh.lock"

    def record_run(self, data: dict[str, Any]) -> Path:
        completed = float(data.get("completed_at_epoch", time.time()))
        stamp = datetime.fromtimestamp(completed, tz=timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
        status = str(data.get("status", "unknown"))
        path = self.runs_dir / f"{stamp}-{status}.json"
        self._write_json_atomic(path, data)
        self._write_json_atomic(self.latest_path, data)
        return path

    def list_runs(self, limit: int | None = None) -> list[dict[str, Any]]:
        paths = sorted(self.runs_dir.glob("*.json"), reverse=True)
        if limit is not None:
            paths = paths[: max(limit, 0)]
        runs = []
        for path in paths:
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            if isinstance(data, dict):
                runs.append({"path": str(path), **data})
        return runs

    def inspect_lock(self, stale_after_seconds: float = 3600) -> LockStatus:
        if not self.lock_path.exists():
            return LockStatus(False, self.lock_path, None, None, None, False, False)
        malformed = False
        pid = None
        started = None
        try:
            raw = json.loads(self.lock_path.read_text(encoding="utf-8"))
            if not isinstance(raw, dict):
                malformed = True
            else:
                pid = raw.get("pid") if isinstance(raw.get("pid"), int) else None
                started_value = raw.get("started_at_epoch")
                started = float(started_value) if isinstance(started_value, (int, float)) else None
                malformed = pid is None or started is None
        except (OSError, json.JSONDecodeError, ValueError):
            malformed = True
        age = max(0.0, time.time() - started) if started is not None else None
        stale = malformed or (age is not None and age >= stale_after_seconds)
        return LockStatus(True, self.lock_path, pid, started, age, stale, malformed)

    def clear_stale_lock(self, stale_after_seconds: float = 3600) -> LockStatus:
        status = self.inspect_lock(stale_after_seconds)
        if not status.exists:
            return status
        if not status.stale:
            raise RuntimeError(f"lock is not stale: {self.lock_path}")
        self.lock_path.unlink()
        return status

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
