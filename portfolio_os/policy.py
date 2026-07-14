from __future__ import annotations

import json
import os
import tempfile
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class PolicyViolation:
    rule: str
    level: str
    expected: str
    actual: Any
    message: str


@dataclass(frozen=True)
class PolicyResult:
    status: str
    violations: tuple[PolicyViolation, ...]
    evaluated_rules: int
    report_path: Path

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "evaluated_rules": self.evaluated_rules,
            "violations": [asdict(item) for item in self.violations],
            "summary": {
                "failure_count": sum(item.level == "fail" for item in self.violations),
                "warning_count": sum(item.level == "warn" for item in self.violations),
            },
            "report_path": str(self.report_path),
        }


class PortfolioPolicy:
    """Evaluate explicit portfolio health rules against generated artifacts."""

    DEFAULT_RULES: dict[str, dict[str, Any]] = {
        "min_analysis_coverage": {"value": 0.0, "level": "fail"},
        "max_dirty_count": {"value": 0, "level": "warn"},
        "max_inaccessible_count": {"value": 0, "level": "warn"},
        "max_analysis_errors": {"value": 0, "level": "fail"},
        "max_regressions": {"value": 0, "level": "warn"},
        "min_history_snapshots": {"value": 1, "level": "warn"},
        "require_pipeline_completed": {"value": False, "level": "fail"},
    }

    def __init__(self, workspace: Path, policy_path: Path | None = None) -> None:
        self.workspace = workspace.expanduser().resolve()
        self.policy_path = policy_path.expanduser().resolve() if policy_path else None
        self.report_path = self.workspace / "policy" / "latest-policy.json"

    def evaluate(self) -> PolicyResult:
        rules = self._load_rules()
        summary = self._read_json(self.workspace / "portfolio" / "portfolio-summary.json")
        trends = self._read_json(self.workspace / "trends" / "portfolio-trends.json", required=False) or {}
        pipeline = self._read_json(self.workspace / "pipeline" / "latest-run.json", required=False) or {}
        metrics = summary.get("summary", {})
        violations: list[PolicyViolation] = []

        checks = {
            "min_analysis_coverage": (
                metrics.get("analysis_coverage", 0),
                lambda actual, expected: actual >= expected,
                lambda expected: f">= {expected}",
            ),
            "max_dirty_count": (
                metrics.get("dirty_count", 0),
                lambda actual, expected: actual <= expected,
                lambda expected: f"<= {expected}",
            ),
            "max_inaccessible_count": (
                metrics.get("inaccessible_count", 0),
                lambda actual, expected: actual <= expected,
                lambda expected: f"<= {expected}",
            ),
            "max_analysis_errors": (
                metrics.get("analysis_errors", 0),
                lambda actual, expected: actual <= expected,
                lambda expected: f"<= {expected}",
            ),
            "max_total_findings": (
                metrics.get("total_findings", 0),
                lambda actual, expected: actual <= expected,
                lambda expected: f"<= {expected}",
            ),
            "max_regressions": (
                len(trends.get("regressions", [])),
                lambda actual, expected: actual <= expected,
                lambda expected: f"<= {expected}",
            ),
            "min_history_snapshots": (
                trends.get("snapshot_count", 0),
                lambda actual, expected: actual >= expected,
                lambda expected: f">= {expected}",
            ),
            "require_pipeline_completed": (
                pipeline.get("status") == "completed",
                lambda actual, expected: actual is expected,
                lambda expected: str(bool(expected)).lower(),
            ),
        }

        evaluated = 0
        for rule, config in rules.items():
            if rule not in checks or not config.get("enabled", True):
                continue
            level = str(config.get("level", "fail"))
            if level not in {"fail", "warn"}:
                raise ValueError(f"invalid policy level for {rule}: {level}")
            expected = config.get("value")
            actual, predicate, expectation = checks[rule]
            evaluated += 1
            if predicate(actual, expected):
                continue
            violations.append(
                PolicyViolation(
                    rule=rule,
                    level=level,
                    expected=expectation(expected),
                    actual=actual,
                    message=f"{rule} expected {expectation(expected)}, observed {actual}",
                )
            )

        status = "failed" if any(item.level == "fail" for item in violations) else "passed"
        result = PolicyResult(status, tuple(violations), evaluated, self.report_path)
        self._write_json_atomic(self.report_path, result.to_dict())
        return result

    def _load_rules(self) -> dict[str, dict[str, Any]]:
        rules = {name: dict(config) for name, config in self.DEFAULT_RULES.items()}
        if not self.policy_path:
            return rules
        raw = self._read_json(self.policy_path)
        supplied = raw.get("rules", raw)
        if not isinstance(supplied, dict):
            raise ValueError("policy rules must be a JSON object")
        for name, config in supplied.items():
            if not isinstance(config, dict):
                raise ValueError(f"policy rule must be an object: {name}")
            rules[name] = {**rules.get(name, {}), **config}
        return rules

    @staticmethod
    def _read_json(path: Path, required: bool = True) -> dict[str, Any] | None:
        if not path.exists():
            if required:
                raise FileNotFoundError(f"required artifact not found: {path}")
            return None
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError(f"JSON object required: {path}")
        return data

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
