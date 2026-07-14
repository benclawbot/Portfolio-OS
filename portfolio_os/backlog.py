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
class BacklogItem:
    id: str
    title: str
    repository: str
    category: str
    evidence: tuple[str, ...]
    expected_impact: int
    effort: int
    risk: int
    confidence: float
    priority_score: float
    acceptance_criteria: tuple[str, ...]
    verification_plan: tuple[str, ...]
    status: str = "proposed"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class BacklogResult:
    json_path: Path
    markdown_path: Path
    item_count: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "json_path": str(self.json_path),
            "markdown_path": str(self.markdown_path),
            "item_count": self.item_count,
        }


class PortfolioBacklog:
    """Generate a deterministic, evidence-backed work queue from portfolio analysis."""

    def __init__(self, workspace: Path) -> None:
        self.workspace = workspace.expanduser().resolve()
        self.summary_path = self.workspace / "portfolio" / "portfolio-summary.json"
        self.output_dir = self.workspace / "backlog"
        self.json_path = self.output_dir / "portfolio-backlog.json"
        self.markdown_path = self.output_dir / "portfolio-backlog.md"

    def build(self) -> BacklogResult:
        data = json.loads(self.summary_path.read_text(encoding="utf-8"))
        repositories = data.get("repositories", [])
        items: list[BacklogItem] = []
        for repository in repositories:
            if not isinstance(repository, dict):
                continue
            items.extend(self._recommendations(repository))
        items.sort(key=lambda item: (-item.priority_score, item.repository.lower(), item.id))
        payload = {
            "schema_version": 1,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "source_summary": str(self.summary_path),
            "summary": {
                "item_count": len(items),
                "repository_count": len({item.repository for item in items}),
                "highest_priority": items[0].priority_score if items else 0.0,
            },
            "items": [item.to_dict() for item in items],
        }
        self._write_text_atomic(self.json_path, json.dumps(payload, indent=2, sort_keys=True) + "\n")
        self._write_text_atomic(self.markdown_path, self._render(payload))
        return BacklogResult(self.json_path, self.markdown_path, len(items))

    def _recommendations(self, repository: dict[str, Any]) -> list[BacklogItem]:
        full_name = str(repository.get("full_name") or repository.get("name") or "unknown")
        recommendations: list[BacklogItem] = []
        intelligence = repository.get("intelligence", {}).get("scores", {})

        if not repository.get("analysis_available"):
            recommendations.append(
                self._item(
                    full_name,
                    "analysis",
                    "Restore implementation analysis coverage",
                    ("No persisted implementation analysis is available.",),
                    impact=8,
                    effort=2,
                    risk=1,
                    confidence=0.98,
                    acceptance=("A current analysis artifact exists for the repository HEAD.",),
                    verification=("Run portfolio-refresh and confirm analysis_available is true.",),
                )
            )
        if not repository.get("github_index_available") and repository.get("accessible", True):
            recommendations.append(
                self._item(
                    full_name,
                    "github-index",
                    "Restore GitHub metadata indexing",
                    ("No normalized GitHub metadata artifact is available.",),
                    impact=7,
                    effort=2,
                    risk=1,
                    confidence=0.98,
                    acceptance=("Branch, release, issue, pull-request and check metadata are indexed.",),
                    verification=("Run portfolio-github-index and confirm the repository status is indexed.",),
                )
            )
        if repository.get("dirty"):
            recommendations.append(
                self._item(
                    full_name,
                    "workspace",
                    "Resolve dirty managed checkout",
                    ("The managed checkout contains uncommitted changes and cannot be updated safely.",),
                    impact=8,
                    effort=3,
                    risk=4,
                    confidence=1.0,
                    acceptance=("The checkout is clean or intentionally excluded from management.",),
                    verification=("Run git status and portfolio-refresh; the repository is no longer reported dirty.",),
                )
            )
        if not repository.get("accessible", True):
            recommendations.append(
                self._item(
                    full_name,
                    "access",
                    "Resolve repository access or retirement state",
                    ("GitHub discovery no longer returns this repository.",),
                    impact=6,
                    effort=3,
                    risk=2,
                    confidence=0.9,
                    acceptance=("Access is restored or the repository is explicitly marked retired/superseded.",),
                    verification=("Run synchronization and confirm an explicit accessible or retired state.",),
                )
            )
        if repository.get("archived"):
            return recommendations

        release = intelligence.get("release_readiness", {})
        security = intelligence.get("security", {})
        debt = intelligence.get("technical_debt", {})
        architecture = intelligence.get("architecture", {})

        if int(release.get("score", 100) or 0) < 60:
            evidence = self._negative_evidence(release)
            recommendations.append(
                self._item(
                    full_name,
                    "release-readiness",
                    "Raise release readiness above 60",
                    evidence or ("Release readiness score is below the portfolio threshold.",),
                    impact=9,
                    effort=5,
                    risk=3,
                    confidence=float(release.get("confidence", 0.5) or 0.5),
                    acceptance=("Release-readiness score is at least 60.", "Required checks and tests pass."),
                    verification=("Re-run analysis and GitHub indexing.", "Confirm release_readiness.score >= 60."),
                )
            )
        if int(security.get("score", 100) or 0) < 70:
            evidence = self._negative_evidence(security)
            recommendations.append(
                self._item(
                    full_name,
                    "security",
                    "Remediate highest-impact security gaps",
                    evidence or ("Security score is below 70.",),
                    impact=10,
                    effort=6,
                    risk=5,
                    confidence=float(security.get("confidence", 0.5) or 0.5),
                    acceptance=("Critical findings are zero.", "Security score is at least 70."),
                    verification=("Run security-focused analyzers and repository checks.",),
                )
            )
        if int(debt.get("score", 100) or 0) < 65:
            evidence = self._negative_evidence(debt)
            recommendations.append(
                self._item(
                    full_name,
                    "technical-debt",
                    "Reduce technical debt with targeted tests and fixes",
                    evidence or ("Technical-debt score is below 65.",),
                    impact=7,
                    effort=5,
                    risk=2,
                    confidence=float(debt.get("confidence", 0.5) or 0.5),
                    acceptance=("Technical-debt score is at least 65.", "No new high-severity findings are introduced."),
                    verification=("Run repository tests and Portfolio OS analysis.",),
                )
            )
        if int(architecture.get("score", 100) or 0) < 65:
            evidence = self._negative_evidence(architecture)
            recommendations.append(
                self._item(
                    full_name,
                    "architecture",
                    "Improve architecture quality and documentation",
                    evidence or ("Architecture score is below 65.",),
                    impact=6,
                    effort=6,
                    risk=3,
                    confidence=float(architecture.get("confidence", 0.5) or 0.5),
                    acceptance=("Architecture score is at least 65.", "Architecture evidence is documented."),
                    verification=("Regenerate architecture documentation and re-run analysis.",),
                )
            )
        return recommendations

    @staticmethod
    def _negative_evidence(score: dict[str, Any]) -> tuple[str, ...]:
        factors = score.get("factors", []) if isinstance(score, dict) else []
        return tuple(
            str(factor.get("evidence"))
            for factor in factors
            if isinstance(factor, dict) and int(factor.get("impact", 0) or 0) < 0 and factor.get("evidence")
        )

    def _item(
        self,
        repository: str,
        category: str,
        title: str,
        evidence: tuple[str, ...],
        *,
        impact: int,
        effort: int,
        risk: int,
        confidence: float,
        acceptance: tuple[str, ...],
        verification: tuple[str, ...],
    ) -> BacklogItem:
        digest = hashlib.sha256(f"{repository}|{category}|{title}".encode()).hexdigest()[:12]
        priority = round((impact * confidence * 10) / max(1, effort + risk * 0.5), 2)
        return BacklogItem(
            id=f"rec-{digest}",
            title=title,
            repository=repository,
            category=category,
            evidence=evidence,
            expected_impact=impact,
            effort=effort,
            risk=risk,
            confidence=round(confidence, 3),
            priority_score=priority,
            acceptance_criteria=acceptance,
            verification_plan=verification,
        )

    @staticmethod
    def _render(payload: dict[str, Any]) -> str:
        lines = ["# Portfolio Backlog", "", f"Items: **{payload['summary']['item_count']}**", ""]
        for item in payload["items"]:
            lines.extend(
                [
                    f"## {item['title']}",
                    "",
                    f"- ID: `{item['id']}`",
                    f"- Repository: `{item['repository']}`",
                    f"- Category: `{item['category']}`",
                    f"- Priority: **{item['priority_score']:.2f}**",
                    f"- Impact / effort / risk: **{item['expected_impact']} / {item['effort']} / {item['risk']}**",
                    f"- Confidence: **{item['confidence']:.1%}**",
                    "",
                    "### Evidence",
                    "",
                ]
            )
            lines.extend(f"- {value}" for value in item["evidence"])
            lines.extend(["", "### Acceptance criteria", ""])
            lines.extend(f"- {value}" for value in item["acceptance_criteria"])
            lines.extend(["", "### Verification", ""])
            lines.extend(f"- {value}" for value in item["verification_plan"])
            lines.append("")
        if not payload["items"]:
            lines.append("No evidence-backed work is currently recommended.")
        return "\n".join(lines).rstrip() + "\n"

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
