from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ScoreFactor:
    key: str
    impact: int
    evidence: str

    def to_dict(self) -> dict[str, Any]:
        return {"key": self.key, "impact": self.impact, "evidence": self.evidence}


@dataclass(frozen=True)
class IntelligenceScore:
    name: str
    score: int
    confidence: float
    factors: tuple[ScoreFactor, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "score": self.score,
            "confidence": self.confidence,
            "factors": [factor.to_dict() for factor in self.factors],
        }


class RepositoryIntelligence:
    """Compute deterministic scores from persisted evidence without inventing facts."""

    def evaluate(
        self,
        record: dict[str, Any],
        analysis: dict[str, Any] | None,
        github: dict[str, Any] | None,
    ) -> dict[str, Any]:
        scores = (
            self._architecture(record, analysis),
            self._technical_debt(record, analysis),
            self._security(record, analysis, github),
            self._release_readiness(record, analysis, github),
        )
        return {
            "schema_version": 1,
            "overall_score": round(sum(item.score for item in scores) / len(scores)),
            "scores": {item.name: item.to_dict() for item in scores},
        }

    def _architecture(self, record: dict[str, Any], analysis: dict[str, Any] | None) -> IntelligenceScore:
        factors: list[ScoreFactor] = []
        if analysis is None:
            factors.append(ScoreFactor("missing-analysis", -35, "No persisted implementation analysis is available."))
        else:
            factors.append(ScoreFactor("analysis-evidence", 10, "Implementation evidence is available."))
        frameworks = record.get("frameworks", []) or []
        if frameworks:
            factors.append(ScoreFactor("framework-detection", 5, f"Detected frameworks: {', '.join(frameworks)}."))
        file_count = int(record.get("file_count", 0) or 0)
        if file_count >= 25:
            factors.append(ScoreFactor("substantial-codebase", 5, f"Repository contains {file_count} analyzed files."))
        elif 0 < file_count < 5:
            factors.append(ScoreFactor("very-small-codebase", -10, f"Only {file_count} analyzed files were detected."))
        self._finding_penalties(record, factors)
        return self._finish("architecture", 60, factors, analysis is not None)

    def _technical_debt(self, record: dict[str, Any], analysis: dict[str, Any] | None) -> IntelligenceScore:
        factors: list[ScoreFactor] = []
        file_count = int(record.get("file_count", 0) or 0)
        test_count = int(record.get("test_file_count", 0) or 0)
        if analysis is None:
            factors.append(ScoreFactor("missing-analysis", -30, "Technical debt cannot be assessed fully without analysis."))
        if file_count and test_count:
            ratio = test_count / file_count
            impact = 15 if ratio >= 0.1 else 5
            factors.append(ScoreFactor("test-presence", impact, f"Detected {test_count} test files for {file_count} files."))
        elif file_count:
            factors.append(ScoreFactor("no-tests-detected", -25, f"No test files were detected across {file_count} files."))
        finding_count = int(record.get("finding_count", 0) or 0)
        if finding_count:
            factors.append(ScoreFactor("findings", -min(30, finding_count * 3), f"Analysis reported {finding_count} findings."))
        if record.get("dirty"):
            factors.append(ScoreFactor("dirty-worktree", -10, "Managed checkout has uncommitted changes."))
        return self._finish("technical_debt", 65, factors, analysis is not None)

    def _security(
        self,
        record: dict[str, Any],
        analysis: dict[str, Any] | None,
        github: dict[str, Any] | None,
    ) -> IntelligenceScore:
        factors: list[ScoreFactor] = []
        severity = record.get("severity_counts", {}) or {}
        critical = int(severity.get("critical", 0) or 0)
        high = int(severity.get("high", 0) or 0)
        if critical:
            factors.append(ScoreFactor("critical-findings", -min(50, critical * 15), f"Detected {critical} critical findings."))
        if high:
            factors.append(ScoreFactor("high-findings", -min(35, high * 10), f"Detected {high} high-severity findings."))
        if record.get("visibility") == "private":
            factors.append(ScoreFactor("private-repository", 5, "Repository visibility is private."))
        branches = (github or {}).get("branches", [])
        default = record.get("default_branch")
        protected = any(item.get("name") == default and item.get("protected") for item in branches)
        if branches:
            factors.append(ScoreFactor("default-branch-protection", 15 if protected else -15, f"Default branch protection is {'enabled' if protected else 'not detected'}."))
        elif github is None:
            factors.append(ScoreFactor("missing-github-index", -10, "GitHub protection and check evidence is unavailable."))
        return self._finish("security", 70, factors, analysis is not None or github is not None)

    def _release_readiness(
        self,
        record: dict[str, Any],
        analysis: dict[str, Any] | None,
        github: dict[str, Any] | None,
    ) -> IntelligenceScore:
        factors: list[ScoreFactor] = []
        if record.get("archived"):
            factors.append(ScoreFactor("archived", -50, "Repository is archived."))
        if not record.get("accessible", True):
            factors.append(ScoreFactor("inaccessible", -40, "Repository is not currently accessible."))
        if record.get("dirty"):
            factors.append(ScoreFactor("dirty-worktree", -20, "Managed checkout is dirty."))
        if int(record.get("error_count", 0) or 0):
            factors.append(ScoreFactor("analysis-errors", -20, "Implementation analysis contains errors."))
        if int(record.get("test_file_count", 0) or 0):
            factors.append(ScoreFactor("tests-detected", 10, "Test files are present."))
        if github is not None:
            summary = github.get("summary", {})
            state = summary.get("combined_status")
            if state == "success":
                factors.append(ScoreFactor("checks-passing", 20, "Default-branch combined status is successful."))
            elif state in {"failure", "error"}:
                factors.append(ScoreFactor("checks-failing", -30, f"Default-branch combined status is {state}."))
            releases = int(summary.get("release_count", 0) or 0)
            tags = int(summary.get("tag_count", 0) or 0)
            if releases:
                factors.append(ScoreFactor("published-release", 10, f"Detected {releases} published or draft releases."))
            elif tags:
                factors.append(ScoreFactor("version-tags", 5, f"Detected {tags} tags."))
        else:
            factors.append(ScoreFactor("missing-github-index", -15, "GitHub release and check evidence is unavailable."))
        return self._finish("release_readiness", 60, factors, analysis is not None or github is not None)

    @staticmethod
    def _finding_penalties(record: dict[str, Any], factors: list[ScoreFactor]) -> None:
        error_count = int(record.get("error_count", 0) or 0)
        if error_count:
            factors.append(ScoreFactor("analysis-errors", -min(25, error_count * 5), f"Analysis reported {error_count} errors."))
        severity = record.get("severity_counts", {}) or {}
        high = int(severity.get("high", 0) or 0) + int(severity.get("critical", 0) or 0)
        if high:
            factors.append(ScoreFactor("high-severity-findings", -min(25, high * 5), f"Detected {high} high or critical findings."))

    @staticmethod
    def _finish(name: str, base: int, factors: list[ScoreFactor], evidence_available: bool) -> IntelligenceScore:
        score = max(0, min(100, base + sum(factor.impact for factor in factors)))
        confidence = 0.9 if evidence_available else 0.35
        return IntelligenceScore(name, score, confidence, tuple(factors))
