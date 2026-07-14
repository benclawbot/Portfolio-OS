from __future__ import annotations

import hashlib
import json
import os
import tempfile
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class WorkspaceCheck:
    name: str
    status: str
    path: str
    message: str


@dataclass(frozen=True)
class WorkspaceValidation:
    status: str
    checks: tuple[WorkspaceCheck, ...]
    manifest_path: Path

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": 1,
            "status": self.status,
            "checks": [asdict(check) for check in self.checks],
            "summary": {
                "passed": sum(check.status == "passed" for check in self.checks),
                "warnings": sum(check.status == "warning" for check in self.checks),
                "failed": sum(check.status == "failed" for check in self.checks),
            },
            "manifest_path": str(self.manifest_path),
        }


class WorkspaceValidator:
    """Validate persisted Portfolio OS artifacts and emit a content manifest."""

    ARTIFACTS = {
        "sync_state": ("sync-state.json", True),
        "github_index": ("github/index.json", False),
        "portfolio_summary": ("portfolio/portfolio-summary.json", True),
        "portfolio_report": ("portfolio/portfolio-report.md", True),
        "portfolio_graph": ("portfolio/portfolio-graph.json", True),
        "history_latest": ("history/latest.json", True),
        "history_delta": ("history/latest-delta.json", True),
        "trends": ("trends/portfolio-trends.json", True),
        "dashboard": ("dashboard/index.html", True),
        "dashboard_data": ("dashboard/dashboard-data.json", True),
        "pipeline_latest": ("pipeline/latest-run.json", False),
        "policy_latest": ("policy/latest-policy.json", False),
    }

    def __init__(self, workspace: Path) -> None:
        self.workspace = workspace.expanduser().resolve()
        self.manifest_path = self.workspace / "workspace" / "manifest.json"

    def validate(self) -> WorkspaceValidation:
        checks: list[WorkspaceCheck] = []
        manifest: dict[str, Any] = {"schema_version": 1, "workspace": str(self.workspace), "artifacts": {}}
        for name, (relative, required) in self.ARTIFACTS.items():
            path = self.workspace / relative
            if not path.exists():
                status = "failed" if required else "warning"
                checks.append(WorkspaceCheck(name, status, str(path), "artifact is missing"))
                continue
            try:
                raw = path.read_bytes()
            except OSError as error:
                checks.append(WorkspaceCheck(name, "failed", str(path), f"artifact cannot be read: {error}"))
                continue
            if path.suffix == ".json":
                try:
                    parsed = json.loads(raw.decode("utf-8"))
                except (UnicodeDecodeError, json.JSONDecodeError) as error:
                    checks.append(WorkspaceCheck(name, "failed", str(path), f"invalid JSON: {error}"))
                    continue
                if not isinstance(parsed, dict):
                    checks.append(WorkspaceCheck(name, "failed", str(path), "JSON root must be an object"))
                    continue
            digest = hashlib.sha256(raw).hexdigest()
            manifest["artifacts"][name] = {"path": relative, "sha256": digest, "size_bytes": len(raw)}
            checks.append(WorkspaceCheck(name, "passed", str(path), "artifact is readable"))
        status = "failed" if any(check.status == "failed" for check in checks) else "passed"
        result = WorkspaceValidation(status, tuple(checks), self.manifest_path)
        manifest["validation"] = result.to_dict()["summary"]
        self._write_json_atomic(self.manifest_path, manifest)
        return result

    def repair_plan(self) -> dict[str, Any]:
        validation = self.validate()
        failed = {check.name for check in validation.checks if check.status == "failed"}
        warnings = {check.name for check in validation.checks if check.status == "warning"}
        stages = []
        if "sync_state" in failed:
            stages.append("sync")
        if "github_index" in failed | warnings:
            stages.append("github-index")
        if failed & {"portfolio_summary", "portfolio_report", "portfolio_graph", "history_latest", "history_delta"}:
            stages.append("report")
        if "trends" in failed:
            stages.append("trends")
        if failed & {"dashboard", "dashboard_data"}:
            stages.append("dashboard")
        return {
            "status": validation.status,
            "stages": list(dict.fromkeys(stages)),
            "checks": [asdict(check) for check in validation.checks if check.status != "passed"],
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
