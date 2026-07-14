# Portfolio OS

Private governance and automation for the `benclawbot` GitHub portfolio.

Portfolio OS inventories repositories, analyzes implementation evidence, generates code-derived documentation, compares repository DNA, builds an explainable portfolio knowledge graph, safely synchronizes a managed local workspace, produces portfolio-wide reports, tracks portfolio changes over time, identifies multi-period trends, generates an offline static dashboard, refreshes the complete system through one locked pipeline, and enforces explicit portfolio and repository health policies. Destructive portfolio actions remain disabled by default.

## Core workflow

```bash
export GITHUB_TOKEN=github_pat_...
portfolio-refresh --pretty
portfolio-refresh --policy portfolio-policy.example.json --pretty
```

A refresh synchronizes safe local checkouts, analyzes changed repositories, rebuilds reports and the knowledge graph, records history, generates trends and the dashboard, and can enforce a policy as its final stage.

## Repository analysis and documentation

```bash
python -m portfolio_os.cli analyze /path/to/repository --pretty
python -m portfolio_os.cli readme /path/to/repository --diff
python -m portfolio_os.cli readme /path/to/repository --write
python -m portfolio_os.cli dna /path/to/repository
python -m portfolio_os.cli compare /path/to/repo-a /path/to/repo-b --pretty
```

Generated README content is based on implementation evidence and preserves the existing leading hero banner. See [`docs/ANALYSIS-ENGINE.md`](docs/ANALYSIS-ENGINE.md), [`docs/README-GENERATOR.md`](docs/README-GENERATOR.md), and [`docs/REPOSITORY-DNA.md`](docs/REPOSITORY-DNA.md).

## Knowledge graph

```bash
python -m portfolio_os.cli graph-build /path/to/repo-a /path/to/repo-b \
  --output reports/latest/portfolio-graph.json
python -m portfolio_os.cli graph-query reports/latest/portfolio-graph.json repo:repo-a --impact
```

See [`docs/KNOWLEDGE-GRAPH.md`](docs/KNOWLEDGE-GRAPH.md).

## Safe GitHub synchronization

```bash
python -m portfolio_os.cli sync --pretty
python -m portfolio_os.cli workspace-status --pretty
```

Missing repositories are cloned. Existing clean repositories may advance only through fast-forward updates on their checked-out default branch. Dirty trees, other branches, detached HEADs, archived repositories, origin mismatches, path conflicts, and inaccessible repositories are preserved and reported. See [`docs/GITHUB-SYNC.md`](docs/GITHUB-SYNC.md).

## Reports, history, trends, and dashboard

```bash
portfolio-report --pretty
portfolio-trends --pretty
portfolio-dashboard --pretty
```

Portfolio artifacts include analysis coverage, languages, frameworks, findings, repository status, attention queues, immutable snapshots, deltas, multi-period trends, regression signals, and a self-contained offline dashboard. See [`docs/PORTFOLIO-REPORTING.md`](docs/PORTFOLIO-REPORTING.md), [`docs/PORTFOLIO-HISTORY.md`](docs/PORTFOLIO-HISTORY.md), [`docs/PORTFOLIO-TRENDS.md`](docs/PORTFOLIO-TRENDS.md), and [`docs/PORTFOLIO-DASHBOARD.md`](docs/PORTFOLIO-DASHBOARD.md).

## End-to-end refresh pipeline

```bash
portfolio-refresh --pretty
portfolio-refresh --skip-sync --pretty
portfolio-refresh --enforce-policy --pretty
portfolio-refresh --policy portfolio-policy.example.json --pretty
```

The pipeline uses an exclusive workspace lock, records per-stage status and duration, blocks dependent stages after failure by default, and writes `<workspace>/pipeline/latest-run.json`. A fail-level policy violation marks the entire refresh failed. See [`docs/REFRESH-PIPELINE.md`](docs/REFRESH-PIPELINE.md).

## Portfolio and repository policies

```bash
portfolio-policy --pretty
portfolio-policy --policy portfolio-policy.example.json --pretty
```

Portfolio OS `0.14.0` supports strict schema validation and exact repository-specific rules for analysis availability, accessibility, dirty state, tests, findings, and analyzer errors. Unknown sections, rules, fields, and invalid value types fail clearly instead of being silently ignored. See [`docs/PORTFOLIO-POLICY.md`](docs/PORTFOLIO-POLICY.md).

## Production foundation

```bash
cp portfolio-os.example.json portfolio-os.json
python -m portfolio_os.cli --runtime-config portfolio-os.json analyze . --pretty
python -m portfolio_os.cli --json-logs --log-level DEBUG analyze . --pretty
python -m portfolio_os.cli plugins
```

External analyzer packages can register through the `portfolio_os.analyzers` entry-point group. See [`docs/PRODUCTION-FOUNDATION.md`](docs/PRODUCTION-FOUNDATION.md).

## Development

```bash
python -m pip install -e ".[dev]"
python -m compileall -q portfolio_os
python -m ruff check portfolio_os tests
python -m pytest -q --cov=portfolio_os --cov-report=term-missing
```

## Safety defaults

- Archive actions are recommendation-only.
- Pull-request actions are analysis-only.
- Existing README hero banners are preserved.
- README replacement requires explicit `--write`.
- GitHub synchronization never resets, rebases, cleans, force-updates, deletes branches, or deletes local repositories.
- Dirty working trees and non-default branches are preserved and reported.
- Historical snapshots contain derived evidence only.
- Snapshot deletion requires an explicit retention apply flag and always preserves at least one snapshot.
- Dashboard generation writes only static output files.
- Concurrent refreshes are rejected through an exclusive workspace lock.
- Policy evaluation writes only a derived policy report.

Portfolio-level decisions live under [`docs/`](docs/), with the machine-readable inventory in [`config/portfolio.json`](config/portfolio.json).
