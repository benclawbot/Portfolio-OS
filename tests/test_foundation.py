from __future__ import annotations

import json
import logging
from pathlib import Path

import pytest

from portfolio_os.analyzers.base import Analyzer, AnalyzerResult
from portfolio_os.config import PortfolioConfig, load_runtime_config
from portfolio_os.engine import AnalysisEngine
from portfolio_os.logging import JsonFormatter
from portfolio_os.plugins import PluginRegistry


class FirstAnalyzer(Analyzer):
    name = "first"

    def analyze(self, root: Path) -> AnalyzerResult:
        return AnalyzerResult({"ok": True}, [])


class DuplicateAnalyzer(Analyzer):
    name = "first"

    def analyze(self, root: Path) -> AnalyzerResult:
        return AnalyzerResult({}, [])


def test_runtime_config_defaults_when_missing(tmp_path: Path) -> None:
    config = load_runtime_config(tmp_path / "missing.json")
    assert config.workspace == Path(".portfolio-os")
    assert config.analysis.fail_on_plugin_error is False


def test_runtime_config_loads_json(tmp_path: Path) -> None:
    path = tmp_path / "config.json"
    path.write_text(json.dumps({"workspace": "work", "analysis": {"enabled_analyzers": ["first"]}, "logging": {"level": "debug", "json": True}}), encoding="utf-8")
    config = load_runtime_config(path)
    assert config.workspace == Path("work")
    assert config.analysis.enabled_analyzers == ("first",)
    assert config.logging.level == "DEBUG"
    assert config.logging.json is True


def test_plugin_registry_filters_and_rejects_unknown() -> None:
    registry = PluginRegistry((FirstAnalyzer,))
    assert [plugin.name for plugin in registry.instantiate()] == ["first"]
    assert registry.instantiate(disabled=("first",)) == ()
    with pytest.raises(KeyError):
        registry.instantiate(enabled=("missing",))


def test_plugin_registry_rejects_duplicate_name() -> None:
    registry = PluginRegistry((FirstAnalyzer,))
    with pytest.raises(ValueError):
        registry.register(DuplicateAnalyzer, source="test")


def test_engine_uses_configured_plugins(tmp_path: Path) -> None:
    config = PortfolioConfig.from_dict({"analysis": {"enabled_analyzers": ["first"]}})
    engine = AnalysisEngine(config=config, registry=PluginRegistry((FirstAnalyzer,)))
    analysis = engine.analyze(tmp_path)
    assert analysis.facts == {"first": {"ok": True}}


def test_json_formatter_emits_machine_readable_context() -> None:
    record = logging.LogRecord("portfolio", logging.INFO, __file__, 1, "done", (), None)
    record.repository = "Medusa"
    payload = json.loads(JsonFormatter().format(record))
    assert payload["repository"] == "Medusa"
    assert payload["level"] == "INFO"
