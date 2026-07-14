from __future__ import annotations

import json
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class TrendResult:
    json_path: Path
    report_path: Path
    data: dict[str, Any]


class PortfolioTrends:
    """Build multi-snapshot portfolio trends and non-destructive retention plans."""

    METRICS = (
        "repository_count",
        "active_count",
        "archived_count",
        "inaccessible_count",
        "dirty_count",
        "analyzed_count",
        "analysis_coverage",
        "total_files",
        "total_test_files",
        "total_findings",
        "analysis_errors",
    )

    def __init__(self, workspace: Path, output_dir: Path | None = None) -> None:
        self.workspace = workspace.expanduser().resolve()
        self.snapshots_dir = self.workspace / "history" / "snapshots"
        self.output_dir = (output_dir or self.workspace / "trends").expanduser().resolve()

    def build(self, limit: int | None = None) -> TrendResult:
        snapshots = self._load_snapshots()
        if limit is not None:
            snapshots = snapshots[-max(limit, 0) :]
        data = self._analyze(snapshots)
        json_path = self.output_dir / "portfolio-trends.json"
        report_path = self.output_dir / "portfolio-trends.md"
        self._write_json_atomic(json_path, data)
        self._write_text_atomic(report_path, self._render_markdown(data))
        return TrendResult(json_path, report_path, data)

    def retention_plan(self, keep: int) -> dict[str, Any]:
        if keep < 1:
            raise ValueError("keep must be at least 1")
        paths = sorted(self.snapshots_dir.glob("*.json"))
        remove = paths[:-keep] if len(paths) > keep else []
        return {
            "keep": keep,
            "snapshot_count": len(paths),
            "remove_count": len(remove),
            "remove": [str(path) for path in remove],
        }

    def apply_retention(self, keep: int) -> dict[str, Any]:
        plan = self.retention_plan(keep)
        for raw_path in plan["remove"]:
            Path(raw_path).unlink(missing_ok=True)
        plan["applied"] = True
        return plan

    def _load_snapshots(self) -> list[dict[str, Any]]:
        snapshots = []
        for path in sorted(self.snapshots_dir.glob("*.json")):
            try:
                raw = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            portfolio = raw.get("portfolio")
            if not isinstance(portfolio, dict):
                continue
            snapshots.append(
                {
                    "path": str(path),
                    "recorded_at": raw.get("recorded_at", ""),
                    "fingerprint": raw.get("fingerprint", ""),
                    "portfolio": portfolio,
                }
            )
        return snapshots

    def _analyze(self, snapshots: list[dict[str, Any]]) -> dict[str, Any]:
        timeline = []
        repository_activity: dict[int, dict[str, Any]] = {}
        regressions = []
        previous: dict[str, Any] | None = None
        for snapshot in snapshots:
            portfolio = snapshot["portfolio"]
            summary = portfolio.get("summary", {})
            point = {
                "recorded_at": snapshot["recorded_at"],
                "fingerprint": snapshot["fingerprint"],
                "metrics": {metric: summary.get(metric, 0) for metric in self.METRICS},
            }
            timeline.append(point)
            repositories = {item["id"]: item for item in portfolio.get("repositories", [])}
            for repository_id, repository in repositories.items():
                activity = repository_activity.setdefault(
                    repository_id,
                    {
                        "id": repository_id,
                        "full_name": repository.get("full_name"),
                        "first_seen": snapshot["recorded_at"],
                        "last_seen": snapshot["recorded_at"],
                        "head_changes": 0,
                        "finding_change": 0,
                        "test_file_change": 0,
                    },
                )
                activity["last_seen"] = snapshot["recorded_at"]
                if previous:
                    prior = {
                        item["id"]: item for item in previous.get("repositories", [])
                    }.get(repository_id)
                    if prior:
                        if prior.get("head_sha") != repository.get("head_sha"):
                            activity["head_changes"] += 1
                        activity["finding_change"] += repository.get("finding_count", 0) - prior.get(
                            "finding_count", 0
                        )
                        activity["test_file_change"] += repository.get("test_file_count", 0) - prior.get(
                            "test_file_count", 0
                        )
            if previous:
                prior_summary = previous.get("summary", {})
                for metric, direction in (
                    ("analysis_coverage", "down"),
                    ("dirty_count", "up"),
                    ("inaccessible_count", "up"),
                    ("analysis_errors", "up"),
                    ("total_findings", "up"),
                ):
                    before = prior_summary.get(metric, 0)
                    after = summary.get(metric, 0)
                    regressed = after < before if direction == "down" else after > before
                    if regressed:
                        regressions.append(
                            {
                                "recorded_at": snapshot["recorded_at"],
                                "metric": metric,
                                "before": before,
                                "after": after,
                                "change": after - before,
                            }
                        )
            previous = portfolio

        first = timeline[0]["metrics"] if timeline else {}
        latest = timeline[-1]["metrics"] if timeline else {}
        net_change = {
            metric: latest.get(metric, 0) - first.get(metric, 0) for metric in self.METRICS
        }
        return {
            "schema_version": 1,
            "snapshot_count": len(snapshots),
            "period": {
                "start": timeline[0]["recorded_at"] if timeline else None,
                "end": timeline[-1]["recorded_at"] if timeline else None,
            },
            "timeline": timeline,
            "net_change": net_change,
            "regressions": regressions,
            "repository_activity": sorted(
                repository_activity.values(), key=lambda item: str(item["full_name"])
            ),
        }

    @staticmethod
    def _write_json_atomic(path: Path, data: dict[str, Any]) -> None:
        PortfolioTrends._write_text_atomic(path, json.dumps(data, indent=2, sort_keys=True) + "\n")

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
        lines = [
            "# Portfolio Trends",
            "",
            f"Snapshots: **{data['snapshot_count']}**",
            f"Period: `{data['period']['start'] or 'n/a'}` to `{data['period']['end'] or 'n/a'}`",
            "",
            "## Net change",
            "",
        ]
        lines.extend(f"- {metric}: {change:+}" for metric, change in data["net_change"].items())
        lines.extend(["", "## Regressions", ""])
        if data["regressions"]:
            lines.extend(
                f"- `{item['recorded_at']}` {item['metric']}: {item['before']} → {item['after']}"
                for item in data["regressions"]
            )
        else:
            lines.append("- None detected")
        lines.extend(["", "## Repository activity", ""])
        for item in data["repository_activity"]:
            lines.append(
                f"- `{item['full_name']}` — HEAD changes: {item['head_changes']}; "
                f"findings Δ {item['finding_change']:+}; tests Δ {item['test_file_change']:+}"
            )
        if not data["repository_activity"]:
            lines.append("- No repository history available")
        return "\n".join(lines).rstrip() + "\n"
