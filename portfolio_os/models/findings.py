from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

Severity = Literal["info", "low", "medium", "high", "critical"]
Confidence = Literal["low", "medium", "high"]


@dataclass(frozen=True)
class Evidence:
    path: str
    detail: str
    line: int | None = None


@dataclass(frozen=True)
class Finding:
    analyzer: str
    code: str
    title: str
    severity: Severity
    confidence: Confidence
    summary: str
    recommendation: str | None = None
    evidence: tuple[Evidence, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class RepositoryAnalysis:
    repository: str
    root: str
    generated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    facts: dict[str, Any] = field(default_factory=dict)
    findings: list[Finding] = field(default_factory=list)
    errors: list[dict[str, str]] = field(default_factory=list)

    def add_facts(self, analyzer: str, facts: dict[str, Any]) -> None:
        self.facts[analyzer] = facts

    def add_findings(self, findings: list[Finding]) -> None:
        self.findings.extend(findings)

    def add_error(self, analyzer: str, error: Exception) -> None:
        self.errors.append({"analyzer": analyzer, "error": f"{type(error).__name__}: {error}"})

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["summary"] = {
            "finding_count": len(self.findings),
            "error_count": len(self.errors),
            "severity_counts": {
                severity: sum(1 for finding in self.findings if finding.severity == severity)
                for severity in ("critical", "high", "medium", "low", "info")
            },
        }
        return data

    def write_json(self, path: Path) -> None:
        import json

        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.to_dict(), indent=2) + "\n", encoding="utf-8")
