from __future__ import annotations

import json
import os
import tempfile
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from portfolio_os.operations import RefreshOperations


@dataclass(frozen=True)
class TelemetryResult:
    path: Path
    run_count: int
    failure_count: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "path": str(self.path),
            "run_count": self.run_count,
            "failure_count": self.failure_count,
        }


class TelemetryReporter:
    """Summarize local operational metrics without sending data off-device."""

    def __init__(self, workspace: Path) -> None:
        self.workspace = workspace.expanduser().resolve()
        self.path = self.workspace / "telemetry" / "metrics.json"

    def build(self, limit: int = 200) -> TelemetryResult:
        runs = RefreshOperations(self.workspace).list_runs(limit=limit)
        stage_counts: Counter[str] = Counter()
        stage_failures: Counter[str] = Counter()
        stage_durations: dict[str, list[float]] = {}
        for run in runs:
            for stage in run.get("stages", []):
                if not isinstance(stage, dict):
                    continue
                name = str(stage.get("name", "unknown"))
                status = str(stage.get("status", "unknown"))
                stage_counts[name] += 1
                if status == "failed":
                    stage_failures[name] += 1
                stage_durations.setdefault(name, []).append(float(stage.get("duration_seconds", 0) or 0))
        failure_count = sum(str(run.get("status")) == "failed" for run in runs)
        payload = {
            "schema_version": 1,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "privacy": {
                "scope": "local-workspace-only",
                "network_export": False,
                "contains_source_code": False,
            },
            "summary": {
                "run_count": len(runs),
                "failure_count": failure_count,
                "success_rate": round((len(runs) - failure_count) / len(runs), 4) if runs else 0.0,
            },
            "stages": {
                name: {
                    "run_count": stage_counts[name],
                    "failure_count": stage_failures[name],
                    "average_duration_seconds": round(sum(values) / len(values), 6) if values else 0.0,
                    "maximum_duration_seconds": round(max(values), 6) if values else 0.0,
                }
                for name, values in sorted(stage_durations.items())
            },
        }
        self._write(payload)
        return TelemetryResult(self.path, len(runs), failure_count)

    def _write(self, payload: dict[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        descriptor, temporary_name = tempfile.mkstemp(
            prefix=f".{self.path.name}.", suffix=".tmp", dir=self.path.parent
        )
        temporary = Path(temporary_name)
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
                json.dump(payload, handle, indent=2, sort_keys=True)
                handle.write("\n")
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, self.path)
        finally:
            temporary.unlink(missing_ok=True)
