# Production Foundation

Portfolio OS `0.6.0` introduces a stable runtime foundation for repository analyzers and future GitHub synchronization.

## Runtime configuration

Copy `portfolio-os.example.json` to `portfolio-os.json`, or set `PORTFOLIO_OS_CONFIG` to another path.

```bash
cp portfolio-os.example.json portfolio-os.json
python -m portfolio_os.cli --runtime-config portfolio-os.json analyze . --pretty
```

Configuration controls:

- managed workspace path,
- enabled analyzer allowlist,
- disabled analyzer denylist,
- maximum file size policy reserved for analyzer use,
- whether plugin failures abort analysis,
- text or JSON logging,
- log level.

An empty `enabled_analyzers` list means every registered analyzer is enabled. Unknown plugin names fail early.

## Structured logging

```bash
python -m portfolio_os.cli --json-logs --log-level DEBUG analyze . --pretty
```

JSON records include timestamps, severity, logger, message, and relevant repository, analyzer, command, or duration context.

## Analyzer plugins

Built-in plugins are registered through `PluginRegistry`. External Python distributions can publish analyzer classes using the `portfolio_os.analyzers` entry-point group.

```toml
[project.entry-points."portfolio_os.analyzers"]
custom = "my_package.analyzers:CustomAnalyzer"
```

A plugin must:

1. subclass `portfolio_os.analyzers.Analyzer`,
2. define a globally unique, non-empty `name`,
3. implement `analyze(root: Path) -> AnalyzerResult`,
4. remain read-only unless a separate explicit execution workflow authorizes changes.

List built-in plugins:

```bash
python -m portfolio_os.cli plugins
```

Discover installed entry-point plugins for one analysis:

```bash
python -m portfolio_os.cli analyze . --discover-plugins --pretty
```

## Quality gates

GitHub Actions now enforces:

- Python bytecode compilation,
- Ruff correctness checks,
- pytest with coverage reporting,
- plugin registry smoke testing,
- repository DNA smoke tests,
- knowledge graph smoke tests.

Coverage is currently reported rather than blocked by a numeric threshold. A threshold should be introduced only after the baseline is measured and low-value line execution is not mistaken for meaningful testing.

## Compatibility

The Phase 1 analysis report contract remains unchanged. Configuration and plugins affect which analyzers run, but existing finding, evidence, DNA, README, and graph consumers continue to use the same structured output.
