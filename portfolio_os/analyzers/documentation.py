from __future__ import annotations

import re
from pathlib import Path

from portfolio_os.models import Evidence, Finding
from .base import Analyzer, AnalyzerResult

EXPECTED = ["README.md", "LICENSE", "SECURITY.md", "CHANGELOG.md", "CONTRIBUTING.md"]


class DocumentationAnalyzer(Analyzer):
    name = "documentation"

    def analyze(self, root: Path) -> AnalyzerResult:
        present = {name: (root / name).exists() for name in EXPECTED}
        readme_path = root / "README.md"
        headings: list[str] = []
        hero_banner = None
        readme_bytes = 0
        if readme_path.exists():
            text = readme_path.read_text(encoding="utf-8", errors="replace")
            readme_bytes = len(text.encode("utf-8"))
            headings = [match.group(1).strip() for match in re.finditer(r"^#{1,6}\s+(.+)$", text, re.MULTILINE)]
            image = re.search(r"<img\s+[^>]*src=[\"']([^\"']+)[\"']", text, re.IGNORECASE)
            if image:
                hero_banner = image.group(1)
            else:
                markdown_image = re.search(r"!\[[^\]]*\]\(([^)]+)\)", text)
                if markdown_image:
                    hero_banner = markdown_image.group(1)
        findings: list[Finding] = []
        for name, exists in present.items():
            if not exists:
                severity = "high" if name == "README.md" else "medium" if name in {"LICENSE", "SECURITY.md"} else "low"
                findings.append(Finding(self.name, f"missing-{name.lower()}", f"Missing {name}", severity, "high", f"{name} was not found at the repository root.", f"Add {name} using the Portfolio OS repository standard."))
        if readme_path.exists() and readme_bytes < 300:
            findings.append(Finding(self.name, "readme-too-short", "README contains little project evidence", "medium", "high", f"README.md is only {readme_bytes} bytes.", "Regenerate the README from detected code, commands, tests, and architecture while preserving its hero banner.", (Evidence("README.md", "Short README"),)))
        return AnalyzerResult(facts={"files": present, "readme_bytes": readme_bytes, "headings": headings, "hero_banner": hero_banner}, findings=findings)
