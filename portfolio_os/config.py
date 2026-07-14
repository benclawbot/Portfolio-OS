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
class GitHubSyncConfig:
    owner: str = "benclawbot"
    api_url: str = "https://api.github.com"


@dataclass(frozen=True)
class PortfolioConfig:
    workspace: Path = Path(".portfolio-os")
    profile: str = "default"
    analysis: AnalysisConfig = field(default_factory=AnalysisConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    github: GitHubSyncConfig = field(default_factory=GitHubSyncConfig)

    @classmethod
    def from_dict(cls, data: dict[str, Any], *, profile: str = "default") -> "PortfolioConfig":
        analysis_data = data.get("analysis", {})
        logging_data = data.get("logging", {})
        github_data = data.get("github", {})
        return cls(
            workspace=Path(data.get("workspace", ".portfolio-os")),
            profile=profile,
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
            github=GitHubSyncConfig(
                owner=str(github_data.get("owner", "benclawbot")),
                api_url=str(github_data.get("api_url", "https://api.github.com")),
            ),
        )


def _merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    merged = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def load_runtime_config(path: Path | None = None, profile: str | None = None) -> PortfolioConfig:
    candidate = path or Path(os.environ.get("PORTFOLIO_OS_CONFIG", "portfolio-os.json"))
    selected = profile or os.environ.get("PORTFOLIO_OS_PROFILE", "default")
    if not candidate.exists():
        return PortfolioConfig(profile=selected)
    payload = json.loads(candidate.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("runtime configuration root must be an object")
    profiles = payload.get("profiles", {})
    defaults = {key: value for key, value in payload.items() if key != "profiles"}
    if selected == "default":
        selected_data = defaults
    else:
        if not isinstance(profiles, dict) or selected not in profiles:
            raise ValueError(f"unknown runtime configuration profile: {selected}")
        profile_data = profiles[selected]
        if not isinstance(profile_data, dict):
            raise ValueError(f"runtime configuration profile must be an object: {selected}")
        selected_data = _merge(defaults, profile_data)
    return PortfolioConfig.from_dict(selected_data, profile=selected)
