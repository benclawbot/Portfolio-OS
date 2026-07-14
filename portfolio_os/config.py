from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class AnalysisConfig:
    enabled_analyzers: tuple[str, ...] = ()
    disabled_analyzers: tuple[str, ...] = ()
    max_file_bytes: int = 2_000_000
    fail_on_plugin_error: bool = False


@dataclass(frozen=True)
class LoggingConfig:
    level: str = "INFO"
    json: bool = False


@dataclass(frozen=True)
class PortfolioConfig:
    workspace: Path = Path(".portfolio-os")
    analysis: AnalysisConfig = field(default_factory=AnalysisConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "PortfolioConfig":
        analysis_data = data.get("analysis", {})
        logging_data = data.get("logging", {})
        return cls(
            workspace=Path(data.get("workspace", ".portfolio-os")),
            analysis=AnalysisConfig(
                enabled_analyzers=tuple(analysis_data.get("enabled_analyzers", [])),
                disabled_analyzers=tuple(analysis_data.get("disabled_analyzers", [])),
                max_file_bytes=int(analysis_data.get("max_file_bytes", 2_000_000)),
                fail_on_plugin_error=bool(analysis_data.get("fail_on_plugin_error", False)),
            ),
            logging=LoggingConfig(
                level=str(logging_data.get("level", "INFO")).upper(),
                json=bool(logging_data.get("json", False)),
            ),
        )


def load_runtime_config(path: Path | None = None) -> PortfolioConfig:
    candidate = path or Path(os.environ.get("PORTFOLIO_OS_CONFIG", "portfolio-os.json"))
    if not candidate.exists():
        return PortfolioConfig()
    return PortfolioConfig.from_dict(json.loads(candidate.read_text(encoding="utf-8")))
