from __future__ import annotations

from pathlib import Path

from portfolio_os.models import Finding
from .base import Analyzer, AnalyzerResult, iter_files


class QualityAnalyzer(Analyzer):
    name = "quality"

    def analyze(self, root: Path) -> AnalyzerResult:
        test_files = []
        for path in iter_files(root):
            relative = path.relative_to(root).as_posix().lower()
            name = path.name.lower()
            if "/tests/" in f"/{relative}" or "/test/" in f"/{relative}" or name.startswith("test_") or name.endswith(("_test.py", ".test.ts", ".test.tsx", ".spec.ts", ".spec.tsx", "_test.go")) or relative.endswith("/tests.rs"):
                test_files.append(path.relative_to(root).as_posix())
        workflow_dir = root / ".github" / "workflows"
        workflows = sorted(path.relative_to(root).as_posix() for path in workflow_dir.glob("*.y*ml")) if workflow_dir.exists() else []
        findings: list[Finding] = []
        if not test_files:
            findings.append(Finding(self.name, "no-tests-detected", "No automated tests detected", "high", "medium", "No conventional test files or test directories were found.", "Add tests for the primary user workflow and critical failure paths."))
        if not workflows:
            findings.append(Finding(self.name, "no-github-actions", "No GitHub Actions workflows detected", "medium", "high", "The repository has no workflow YAML under .github/workflows.", "Add CI for formatting, linting, tests, build, and artifact smoke tests."))
        return AnalyzerResult(facts={"test_files": test_files, "test_file_count": len(test_files), "workflows": workflows}, findings=findings)
