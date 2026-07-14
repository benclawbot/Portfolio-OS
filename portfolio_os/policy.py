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
    repository: str | None = None


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
    """Evaluate validated portfolio and repository health rules."""

    PORTFOLIO_RULES = {
        "min_analysis_coverage",
        "max_dirty_count",
        "max_inaccessible_count",
        "max_analysis_errors",
        "max_total_findings",
        "max_regressions",
        "min_history_snapshots",
        "require_pipeline_completed",
    }
    REPOSITORY_RULES = {
        "require_analysis",
        "max_findings",
        "max_analysis_errors",
        "min_test_files",
        "allow_dirty",
        "require_accessible",
    }
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

    def evaluate(self, *, pipeline_status: str | None = None) -> PolicyResult:
        portfolio_rules, repository_rules = self._load_policy()
        summary = self._read_json(self.workspace / "portfolio" / "portfolio-summary.json")
        trends = self._read_json(self.workspace / "trends" / "portfolio-trends.json", required=False) or {}
        pipeline = self._read_json(self.workspace / "pipeline" / "latest-run.json", required=False) or {}
        effective_pipeline_status = pipeline_status if pipeline_status is not None else pipeline.get("status")
        metrics = summary.get("summary", {})
        violations: list[PolicyViolation] = []
        evaluated = 0

        checks = {
            "min_analysis_coverage": (metrics.get("analysis_coverage", 0), "min"),
            "max_dirty_count": (metrics.get("dirty_count", 0), "max"),
            "max_inaccessible_count": (metrics.get("inaccessible_count", 0), "max"),
            "max_analysis_errors": (metrics.get("analysis_errors", 0), "max"),
            "max_total_findings": (metrics.get("total_findings", 0), "max"),
            "max_regressions": (len(trends.get("regressions", [])), "max"),
            "min_history_snapshots": (trends.get("snapshot_count", 0), "min"),
            "require_pipeline_completed": (effective_pipeline_status == "completed", "bool"),
        }
        for rule, config in portfolio_rules.items():
            if not config.get("enabled", True):
                continue
            evaluated += 1
            actual, kind = checks[rule]
            violation = self._violation(rule, config, actual, kind)
            if violation:
                violations.append(violation)

        repositories = {item.get("full_name"): item for item in summary.get("repositories", [])}
        for full_name, rules in repository_rules.items():
            repository = repositories.get(full_name)
            if repository is None:
                violations.append(
                    PolicyViolation("repository_present", "fail", "present", "missing", f"repository policy target not found: {full_name}", full_name)
                )
                evaluated += 1
                continue
            repo_checks = {
                "require_analysis": (bool(repository.get("analysis_available")), "bool"),
                "max_findings": (repository.get("finding_count", 0), "max"),
                "max_analysis_errors": (repository.get("error_count", 0), "max"),
                "min_test_files": (repository.get("test_file_count", 0), "min"),
                "allow_dirty": (bool(repository.get("dirty")), "allow"),
                "require_accessible": (bool(repository.get("accessible")), "bool"),
            }
            for rule, config in rules.items():
                if not config.get("enabled", True):
                    continue
                evaluated += 1
                actual, kind = repo_checks[rule]
                violation = self._violation(rule, config, actual, kind, full_name)
                if violation:
                    violations.append(violation)

        status = "failed" if any(item.level == "fail" for item in violations) else "passed"
        result = PolicyResult(status, tuple(violations), evaluated, self.report_path)
        self._write_json_atomic(self.report_path, result.to_dict())
        return result

    def _load_policy(self) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, dict[str, Any]]]]:
        rules = {name: dict(config) for name, config in self.DEFAULT_RULES.items()}
        repositories: dict[str, dict[str, dict[str, Any]]] = {}
        if not self.policy_path:
            return rules, repositories
        raw = self._read_json(self.policy_path)
        allowed_top = {"rules", "repositories"}
        unknown_top = set(raw) - allowed_top
        if unknown_top:
            raise ValueError(f"unknown policy sections: {', '.join(sorted(unknown_top))}")
        supplied = raw.get("rules", {})
        if not isinstance(supplied, dict):
            raise ValueError("policy rules must be a JSON object")
        unknown_rules = set(supplied) - self.PORTFOLIO_RULES
        if unknown_rules:
            raise ValueError(f"unknown portfolio rules: {', '.join(sorted(unknown_rules))}")
        for name, config in supplied.items():
            rules[name] = {**rules.get(name, {}), **self._validate_rule(name, config)}
        raw_repositories = raw.get("repositories", {})
        if not isinstance(raw_repositories, dict):
            raise ValueError("repositories must be a JSON object")
        for full_name, repo_rules in raw_repositories.items():
            if not isinstance(repo_rules, dict):
                raise ValueError(f"repository rules must be an object: {full_name}")
            unknown = set(repo_rules) - self.REPOSITORY_RULES
            if unknown:
                raise ValueError(f"unknown repository rules for {full_name}: {', '.join(sorted(unknown))}")
            repositories[full_name] = {name: self._validate_rule(name, config) for name, config in repo_rules.items()}
        return rules, repositories

    @staticmethod
    def _validate_rule(name: str, config: Any) -> dict[str, Any]:
        if not isinstance(config, dict):
            raise ValueError(f"policy rule must be an object: {name}")
        unknown = set(config) - {"value", "level", "enabled"}
        if unknown:
            raise ValueError(f"unknown fields for {name}: {', '.join(sorted(unknown))}")
        level = config.get("level", "fail")
        if level not in {"fail", "warn"}:
            raise ValueError(f"invalid policy level for {name}: {level}")
        if "enabled" in config and not isinstance(config["enabled"], bool):
            raise ValueError(f"enabled must be boolean for {name}")
        if "value" not in config:
            raise ValueError(f"policy value is required for {name}")
        return dict(config)

    @staticmethod
    def _violation(rule: str, config: dict[str, Any], actual: Any, kind: str, repository: str | None = None) -> PolicyViolation | None:
        expected = config.get("value")
        level = str(config.get("level", "fail"))
        if kind in {"bool", "allow"} and not isinstance(expected, bool):
            raise ValueError(f"boolean policy value required for {rule}")
        if kind in {"min", "max"} and (not isinstance(expected, (int, float)) or isinstance(expected, bool)):
            raise ValueError(f"numeric policy value required for {rule}")
        passed = {
            "min": actual >= expected,
            "max": actual <= expected,
            "bool": actual is expected,
            "allow": (not actual) or expected,
        }[kind]
        if passed:
            return None
        expression = {"min": f">= {expected}", "max": f"<= {expected}", "bool": str(expected).lower(), "allow": f"allowed={expected}"}[kind]
        scope = f" for {repository}" if repository else ""
        return PolicyViolation(rule, level, expression, actual, f"{rule}{scope} expected {expression}, observed {actual}", repository)

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
