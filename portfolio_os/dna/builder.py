from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Iterable

from portfolio_os.models import RepositoryAnalysis
from .models import DNAFeatureSet, RepositoryDNA

DEFAULT_WEIGHTS = {
    "languages": 0.08,
    "ecosystems": 0.10,
    "frameworks": 0.17,
    "dependencies": 0.22,
    "commands": 0.08,
    "directories": 0.08,
    "entry_points": 0.10,
    "capabilities": 0.17,
}

CAPABILITY_RULES: dict[str, tuple[str, ...]] = {
    "web-frontend": ("react", "next", "vue", "svelte", "@angular/core", "vite"),
    "desktop-app": ("electron", "tauri", "wails", "desktop"),
    "terminal-ui": ("ratatui", "crossterm", "tui", "terminal"),
    "web-api": ("fastapi", "flask", "django", "axum", "actix-web", "express", "api"),
    "automation-cli": ("clap", "argparse", "typer", "click", "commander", "cli"),
    "testing": ("pytest", "vitest", "jest", "playwright", "cypress", "test"),
    "mobile-app": ("flutter", "react-native", "android", "ios", "mobile"),
    "browser-automation": ("playwright", "selenium", "puppeteer", "browser"),
    "ai-agent": ("agent", "llm", "openai", "anthropic", "minimax", "provider", "model"),
    "memory-system": ("memory", "embedding", "vector", "retrieval", "context"),
    "file-transfer": ("transfer", "upload", "download", "webrtc", "websocket", "files"),
}


def _normalize(value: object) -> str:
    text = str(value).strip().lower().replace("\\", "/")
    text = re.sub(r"\s+", "-", text)
    return text.strip("-./")


def _values(items: Iterable[object]) -> tuple[str, ...]:
    return tuple(sorted({_normalize(item) for item in items if _normalize(item)}))


def _language_values(language_facts: dict[str, object]) -> tuple[str, ...]:
    """Read the current analyzer schema while retaining pre-1.0 compatibility."""
    file_counts = language_facts.get("file_counts", {})
    if isinstance(file_counts, dict):
        return _values(file_counts.keys())
    detected = language_facts.get("detected", [])
    if isinstance(detected, (list, tuple, set)):
        return _values(detected)
    return ()


class DNABuilder:
    def __init__(self, weights: dict[str, float] | None = None) -> None:
        self.weights = dict(weights or DEFAULT_WEIGHTS)
        if set(self.weights) != set(DEFAULT_WEIGHTS):
            raise ValueError("DNA weights must define every feature dimension")
        total = sum(self.weights.values())
        if abs(total - 1.0) > 1e-9:
            raise ValueError("DNA weights must sum to 1.0")

    def build(self, analysis: RepositoryAnalysis) -> RepositoryDNA:
        if analysis.errors:
            names = ", ".join(error["analyzer"] for error in analysis.errors)
            raise ValueError(f"Cannot build repository DNA while analyzers failed: {names}")
        facts = analysis.facts
        language_facts = facts.get("languages", {})
        manifest_facts = facts.get("manifests", {})
        repository_facts = facts.get("repository", {})
        languages = _language_values(language_facts)

        dependency_values: list[str] = []
        for ecosystem, dependencies in sorted(manifest_facts.get("dependencies", {}).items()):
            dependency_values.extend(f"{ecosystem}:{dependency}" for dependency in dependencies)

        raw_tokens = set()
        for collection in (
            languages,
            manifest_facts.get("ecosystems", []),
            manifest_facts.get("frameworks", []),
            dependency_values,
            manifest_facts.get("commands", {}).keys(),
            repository_facts.get("top_level_directories", []),
            repository_facts.get("entry_points", []),
        ):
            raw_tokens.update(_normalize(item) for item in collection)
        raw_tokens.add(_normalize(analysis.repository))
        capabilities = self._capabilities(raw_tokens)

        features = DNAFeatureSet(
            languages=languages,
            ecosystems=_values(manifest_facts.get("ecosystems", [])),
            frameworks=_values(manifest_facts.get("frameworks", [])),
            dependencies=_values(dependency_values),
            commands=_values(manifest_facts.get("commands", {}).keys()),
            directories=_values(repository_facts.get("top_level_directories", [])),
            entry_points=_values(repository_facts.get("entry_points", [])),
            capabilities=capabilities,
        )
        payload = json.dumps(features.to_dict(), sort_keys=True, separators=(",", ":"))
        fingerprint = hashlib.sha256(payload.encode("utf-8")).hexdigest()
        evidence_count = sum(len(values) for values in features.to_dict().values())
        return RepositoryDNA(
            repository=analysis.repository,
            fingerprint=fingerprint,
            features=features,
            weights=dict(self.weights),
            evidence_count=evidence_count,
        )

    def _capabilities(self, tokens: set[str]) -> tuple[str, ...]:
        flattened = " ".join(sorted(tokens))
        matched = [
            capability
            for capability, indicators in CAPABILITY_RULES.items()
            if any(indicator in flattened for indicator in indicators)
        ]
        return tuple(sorted(matched))
