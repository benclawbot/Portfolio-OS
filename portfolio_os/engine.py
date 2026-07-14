from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Iterable

from portfolio_os.analyzers import Analyzer
from portfolio_os.config import PortfolioConfig
from portfolio_os.models import RepositoryAnalysis
from portfolio_os.plugins import PluginRegistry

LOGGER = logging.getLogger(__name__)


class AnalysisEngine:
    def __init__(
        self,
        analyzers: Iterable[Analyzer] | None = None,
        *,
        config: PortfolioConfig | None = None,
        registry: PluginRegistry | None = None,
        discover_plugins: bool = False,
    ) -> None:
        self.config = config or PortfolioConfig()
        if analyzers is not None:
            self.analyzers = tuple(analyzers)
            return
        plugin_registry = registry or PluginRegistry()
        if discover_plugins:
            plugin_registry.discover()
        self.analyzers = plugin_registry.instantiate(
            enabled=self.config.analysis.enabled_analyzers,
            disabled=self.config.analysis.disabled_analyzers,
        )

    def analyze(self, root: Path) -> RepositoryAnalysis:
        root = root.expanduser().resolve()
        if not root.exists():
            raise FileNotFoundError(root)
        if not root.is_dir():
            raise NotADirectoryError(root)
        analysis = RepositoryAnalysis(repository=root.name, root=str(root))
        LOGGER.info("repository analysis started", extra={"repository": root.name})
        for analyzer in self.analyzers:
            started = time.perf_counter()
            try:
                result = analyzer.analyze(root)
                analysis.add_facts(analyzer.name, result.facts)
                analysis.add_findings(result.findings)
                LOGGER.debug(
                    "analyzer completed",
                    extra={
                        "repository": root.name,
                        "analyzer": analyzer.name,
                        "duration_ms": round((time.perf_counter() - started) * 1000, 2),
                    },
                )
            except Exception as error:
                analysis.add_error(analyzer.name, error)
                LOGGER.exception(
                    "analyzer failed",
                    extra={"repository": root.name, "analyzer": analyzer.name},
                )
                if self.config.analysis.fail_on_plugin_error:
                    raise
        order = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}
        analysis.findings.sort(key=lambda item: (order[item.severity], item.analyzer, item.code))
        LOGGER.info("repository analysis completed", extra={"repository": root.name})
        return analysis
