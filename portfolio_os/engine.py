from __future__ import annotations

from pathlib import Path
from typing import Iterable

from portfolio_os.analyzers import DEFAULT_ANALYZERS, Analyzer
from portfolio_os.models import RepositoryAnalysis


class AnalysisEngine:
    def __init__(self, analyzers: Iterable[Analyzer] | None = None) -> None:
        self.analyzers = tuple(analyzers) if analyzers is not None else tuple(cls() for cls in DEFAULT_ANALYZERS)

    def analyze(self, root: Path) -> RepositoryAnalysis:
        root = root.expanduser().resolve()
        if not root.exists():
            raise FileNotFoundError(root)
        if not root.is_dir():
            raise NotADirectoryError(root)
        analysis = RepositoryAnalysis(repository=root.name, root=str(root))
        for analyzer in self.analyzers:
            try:
                result = analyzer.analyze(root)
                analysis.add_facts(analyzer.name, result.facts)
                analysis.add_findings(result.findings)
            except Exception as error:
                analysis.add_error(analyzer.name, error)
        order = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}
        analysis.findings.sort(key=lambda item: (order[item.severity], item.analyzer, item.code))
        return analysis
