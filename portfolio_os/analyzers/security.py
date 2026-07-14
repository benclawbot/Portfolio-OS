from __future__ import annotations

import re
from pathlib import Path

from portfolio_os.models import Evidence, Finding
from .base import Analyzer, AnalyzerResult, iter_files

SECRET_PATTERNS = {
    "private-key": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    "github-token": re.compile(r"\bgh[pousr]_[A-Za-z0-9_]{20,}\b"),
    "aws-access-key": re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
}


class SecurityAnalyzer(Analyzer):
    name = "security"

    def analyze(self, root: Path) -> AnalyzerResult:
        candidates: list[Evidence] = []
        ignored = {".env.example", ".env.template", ".env.sample"}
        for path in iter_files(root, max_bytes=500_000):
            relative = path.relative_to(root).as_posix()
            if path.name in ignored or path.suffix.lower() in {".png", ".jpg", ".jpeg", ".gif", ".zip", ".pdf", ".lock"}:
                continue
            try:
                text = path.read_text(encoding="utf-8")
            except (UnicodeDecodeError, OSError):
                continue
            for line_number, line in enumerate(text.splitlines(), 1):
                for kind, pattern in SECRET_PATTERNS.items():
                    if pattern.search(line):
                        candidates.append(Evidence(relative, kind, line_number))
        findings: list[Finding] = []
        if candidates:
            findings.append(Finding(self.name, "possible-secret-material", "Possible secret material detected", "critical", "medium", f"Detected {len(candidates)} value(s) matching high-risk secret patterns.", "Remove and rotate confirmed secrets, then add automated secret scanning.", tuple(candidates[:10])))
        if not (root / ".gitignore").exists():
            findings.append(Finding(self.name, "missing-gitignore", "Missing .gitignore", "medium", "high", "No root .gitignore was found.", "Add language-appropriate ignores for secrets, build outputs, caches, and local environments."))
        return AnalyzerResult(facts={"possible_secrets": [e.__dict__ for e in candidates], "security_policy": (root / "SECURITY.md").exists(), "gitignore": (root / ".gitignore").exists()}, findings=findings)
