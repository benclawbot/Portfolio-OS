from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from portfolio_os.models import Finding

IGNORED_DIRECTORIES = {
    ".git", ".hg", ".svn", ".idea", ".vscode", ".venv", "venv", "env",
    "node_modules", "target", "dist", "build", ".next", ".turbo", ".pytest_cache",
    "__pycache__", "coverage", ".coverage", "vendor", "Pods", ".dart_tool",
}


@dataclass(frozen=True)
class AnalyzerResult:
    facts: dict[str, Any]
    findings: list[Finding]


class Analyzer(ABC):
    name: str

    @abstractmethod
    def analyze(self, root: Path) -> AnalyzerResult:
        raise NotImplementedError


def iter_files(root: Path, *, max_bytes: int | None = None):
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        if any(part in IGNORED_DIRECTORIES for part in path.relative_to(root).parts):
            continue
        if max_bytes is not None:
            try:
                if path.stat().st_size > max_bytes:
                    continue
            except OSError:
                continue
        yield path
