from __future__ import annotations

from collections import Counter
from pathlib import Path

from portfolio_os.models import Finding
from .base import Analyzer, AnalyzerResult, iter_files

EXTENSIONS = {
    ".py": "Python", ".rs": "Rust", ".ts": "TypeScript", ".tsx": "TypeScript",
    ".js": "JavaScript", ".jsx": "JavaScript", ".dart": "Dart", ".go": "Go",
    ".java": "Java", ".kt": "Kotlin", ".kts": "Kotlin", ".swift": "Swift",
    ".cs": "C#", ".cpp": "C++", ".cc": "C++", ".c": "C", ".h": "C/C++ Header",
    ".html": "HTML", ".css": "CSS", ".scss": "SCSS", ".sh": "Shell",
    ".ps1": "PowerShell", ".rb": "Ruby", ".php": "PHP", ".vue": "Vue",
    ".svelte": "Svelte",
}


class LanguageAnalyzer(Analyzer):
    name = "languages"

    def analyze(self, root: Path) -> AnalyzerResult:
        counts: Counter[str] = Counter()
        examples: dict[str, list[str]] = {}
        for path in iter_files(root):
            language = EXTENSIONS.get(path.suffix.lower())
            if not language:
                continue
            counts[language] += 1
            examples.setdefault(language, [])
            if len(examples[language]) < 3:
                examples[language].append(path.relative_to(root).as_posix())
        findings: list[Finding] = []
        if not counts:
            findings.append(Finding(
                analyzer=self.name, code="no-source-language", title="No recognized source language",
                severity="medium", confidence="high",
                summary="No supported source-code extensions were found outside generated directories.",
                recommendation="Confirm the repository contains implementation code or classify it as documentation/reference-only.",
            ))
        return AnalyzerResult(
            facts={"file_counts": dict(counts.most_common()), "primary": counts.most_common(1)[0][0] if counts else None, "examples": examples},
            findings=findings,
        )
