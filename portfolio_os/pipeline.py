from __future__ import annotations

import json
import os
import time
from contextlib import contextmanager
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Callable, Iterator

from portfolio_os.dashboard import PortfolioDashboard
from portfolio_os.history import PortfolioHistory
from portfolio_os.policy import PortfolioPolicy
from portfolio_os.portfolio import PortfolioBuilder
from portfolio_os.trends import PortfolioTrends


@dataclass(frozen=True)
class PipelineStageResult:
    name: str
    status: str
    duration_seconds: float
    output: dict[str, Any]
    error: str | None = None


@dataclass(frozen=True)
class PipelineResult:
    workspace: str
    status: str
    stages: tuple[PipelineStageResult, ...]
    started_at_epoch: float
    completed_at_epoch: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "workspace": self.workspace,
            "status": self.status,
            "stages": [asdict(stage) for stage in self.stages],
            "started_at_epoch": self.started_at_epoch,
            "completed_at_epoch": self.completed_at_epoch,
            "duration_seconds": round(self.completed_at_epoch - self.started_at_epoch, 6),
        }


class PipelineLockedError(RuntimeError):
    pass


class PolicyGateError(RuntimeError):
    pass


class PortfolioPipeline:
    """Run the Portfolio OS refresh stages with locking and durable stage reporting."""

    def __init__(
        self,
        workspace: Path,
        *,
        sync_stage: Callable[[], dict[str, Any]] | None = None,
        similarity_threshold: float = 0.55,
        trend_limit: int | None = None,
        policy_path: Path | None = None,
        enforce_policy: bool = False,
    ) -> None:
        self.workspace = workspace.expanduser().resolve()
        self.sync_stage = sync_stage
        self.similarity_threshold = similarity_threshold
        self.trend_limit = trend_limit
        self.policy_path = policy_path.expanduser().resolve() if policy_path else None
        self.enforce_policy = enforce_policy
        self.lock_path = self.workspace / ".portfolio-os-refresh.lock"
        self.result_path = self.workspace / "pipeline" / "latest-run.json"

    def run(self, *, continue_on_error: bool = False) -> PipelineResult:
        self.workspace.mkdir(parents=True, exist_ok=True)
        started = time.time()
        stages: list[PipelineStageResult] = []
        with self._lock():
            configured = [
                ("sync", self.sync_stage),
                ("report", self._report_stage),
                ("trends", self._trends_stage),
                ("dashboard", self._dashboard_stage),
                ("policy", self._policy_stage if self.enforce_policy else None),
            ]
            blocked = False
            for name, stage in configured:
                if stage is None:
                    stages.append(PipelineStageResult(name, "skipped", 0.0, {}))
                    continue
                if blocked:
                    stages.append(PipelineStageResult(name, "blocked", 0.0, {}))
                    continue
                stage_started = time.perf_counter()
                try:
                    output = stage()
                    duration = time.perf_counter() - stage_started
                    stages.append(PipelineStageResult(name, "completed", duration, output))
                except Exception as error:
                    duration = time.perf_counter() - stage_started
                    stages.append(PipelineStageResult(name, "failed", duration, {}, f"{type(error).__name__}: {error}"))
                    if not continue_on_error:
                        blocked = True
            completed = time.time()
            status = "failed" if any(stage.status == "failed" for stage in stages) else "completed"
            result = PipelineResult(str(self.workspace), status, tuple(stages), started, completed)
            self._write_json_atomic(self.result_path, result.to_dict())
            return result

    def _report_stage(self) -> dict[str, Any]:
        report = PortfolioBuilder(self.workspace).build(self.similarity_threshold)
        history = PortfolioHistory(self.workspace).record(report.data)
        return {
            "summary_path": str(report.summary_path),
            "report_path": str(report.report_path),
            "graph_path": str(report.graph_path),
            "snapshot_path": str(history.snapshot_path),
            "delta_path": str(history.delta_path),
            "delta_summary": history.delta["summary"],
        }

    def _trends_stage(self) -> dict[str, Any]:
        trends = PortfolioTrends(self.workspace).build(self.trend_limit)
        return {
            "json_path": str(trends.json_path),
            "report_path": str(trends.report_path),
            "snapshot_count": trends.data["snapshot_count"],
            "regression_count": len(trends.data["regressions"]),
        }

    def _dashboard_stage(self) -> dict[str, Any]:
        dashboard = PortfolioDashboard(self.workspace).build()
        return {"html_path": str(dashboard.html_path), "data_path": str(dashboard.data_path)}

    def _policy_stage(self) -> dict[str, Any]:
        result = PortfolioPolicy(self.workspace, self.policy_path).evaluate(pipeline_status="completed")
        if result.status == "failed":
            raise PolicyGateError(f"policy failed; report: {result.report_path}")
        return result.to_dict()

    @contextmanager
    def _lock(self) -> Iterator[None]:
        self.lock_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            descriptor = os.open(self.lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        except FileExistsError as error:
            raise PipelineLockedError(f"another refresh appears active: {self.lock_path}") from error
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
                handle.write(json.dumps({"pid": os.getpid(), "started_at_epoch": time.time()}) + "\n")
                handle.flush()
                os.fsync(handle.fileno())
            yield
        finally:
            self.lock_path.unlink(missing_ok=True)

    @staticmethod
    def _write_json_atomic(path: Path, data: dict[str, Any]) -> None:
        import tempfile

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
