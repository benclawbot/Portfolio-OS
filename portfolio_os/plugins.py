from __future__ import annotations

from dataclasses import dataclass
from importlib import metadata
from typing import Iterable

from portfolio_os.analyzers import DEFAULT_ANALYZERS, Analyzer


@dataclass(frozen=True)
class PluginDescriptor:
    name: str
    source: str
    analyzer_type: type[Analyzer]


class PluginRegistry:
    entry_point_group = "portfolio_os.analyzers"

    def __init__(self, builtins: Iterable[type[Analyzer]] = DEFAULT_ANALYZERS) -> None:
        self._plugins: dict[str, PluginDescriptor] = {}
        for analyzer_type in builtins:
            self.register(analyzer_type, source="builtin")

    def register(self, analyzer_type: type[Analyzer], *, source: str) -> None:
        name = analyzer_type.name
        if not name:
            raise ValueError("analyzer plugin name cannot be empty")
        existing = self._plugins.get(name)
        if existing and existing.analyzer_type is not analyzer_type:
            raise ValueError(f"duplicate analyzer plugin: {name}")
        self._plugins[name] = PluginDescriptor(name, source, analyzer_type)

    def discover(self) -> None:
        try:
            entry_points = metadata.entry_points(group=self.entry_point_group)
        except TypeError:
            entry_points = metadata.entry_points().get(self.entry_point_group, ())
        for entry_point in entry_points:
            analyzer_type = entry_point.load()
            if not isinstance(analyzer_type, type) or not issubclass(analyzer_type, Analyzer):
                raise TypeError(f"entry point {entry_point.name} does not expose an Analyzer subclass")
            self.register(analyzer_type, source=f"entry-point:{entry_point.value}")

    def descriptors(self) -> tuple[PluginDescriptor, ...]:
        return tuple(self._plugins[name] for name in sorted(self._plugins))

    def instantiate(
        self,
        *,
        enabled: Iterable[str] = (),
        disabled: Iterable[str] = (),
    ) -> tuple[Analyzer, ...]:
        enabled_set = set(enabled)
        disabled_set = set(disabled)
        unknown = (enabled_set | disabled_set) - self._plugins.keys()
        if unknown:
            raise KeyError(f"unknown analyzer plugins: {', '.join(sorted(unknown))}")
        selected = enabled_set or set(self._plugins)
        selected -= disabled_set
        return tuple(self._plugins[name].analyzer_type() for name in sorted(selected))
