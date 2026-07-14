# Portfolio OS

Private governance and automation for the `benclawbot` GitHub portfolio.

Portfolio OS inventories repositories, analyzes implementation evidence, generates code-derived documentation, compares repository DNA, builds an explainable portfolio knowledge graph, safely synchronizes a managed local workspace, produces portfolio-wide reports, tracks portfolio changes over time, identifies multi-period trends, generates an offline static dashboard, refreshes the complete system through one locked pipeline, and enforces explicit portfolio health policies. Destructive portfolio actions remain disabled by default.

## Phase 1: repository analysis

Analyze any local repository checkout and emit structured JSON covering repository structure, languages, frameworks, manifests, dependencies, tests, CI, documentation, governance, TODO markers, and basic security indicators.

```bash
python -m portfolio_os.cli analyze /path/to/repository --pretty
python -m portfolio_os.cli analyze /path/to/repository \
  --output reports/latest/repository.json
```

See [`docs/ANALYSIS-ENGINE.md`](docs/ANALYSIS-ENGINE.md).

## Phase 2: evidence-based README generation

Generate deterministic documentation from Phase 1 evidence while preserving the existing leading hero banner:

```bash
python -m portfolio_os.cli readme /path/to/repository
python -m portfolio_os.cli readme /path/to/repository --diff
python -m portfolio_os.cli readme /path/to/repository --check
python -m portfolio_os.cli readme /path/to/repository --write
```

Generation stops if an analyzer fails. Existing README body claims are not treated as implementation evidence. See [`docs/README-GENERATOR.md`](docs/README-GENERATOR.md).

## Phase 3: repository DNA

```bash
python -m portfolio_os.cli dna /path/to/repository
python -m portfolio_os.cli compare /path/to/repo-a /path/to/repo-b --pretty
```

Similarity output includes per-dimension overlap, unique evidence on each side, and human-readable reasons. See [`docs/REPOSITORY-DNA.md`](docs/REPOSITORY-DNA.md).

## Phase 4: portfolio knowledge graph

```bash
python -m portfolio_os.cli graph-build /path/to/repo-a /path/to/repo-b \
  --output reports/latest/portfolio-graph.json
python -m portfolio_os.cli graph-query reports/latest/portfolio-graph.json repo:repo-a
python -m portfolio_os.cli graph-query reports/latest/portfolio-graph.json repo:repo-a --impact
python -m portfolio_os.cli graph-path reports/latest/portfolio-graph.json repo:repo-a technology:languages:Python
```

See [`docs/KNOWLEDGE-GRAPH.md`](docs/KNOWLEDGE-GRAPH.md).

## GitHub synchronization and managed workspace

Portfolio OS `0.7.0` discovers repositories owned by the configured account, including private repositories visible to the token, and maintains safe local checkouts.

```bash
export GITHUB_TOKEN=github_pat_...
python -m portfolio_os.cli sync --pretty
python -m portfolio_os.cli workspace-status --pretty
```

Missing repositories are cloned. Existing clean repositories are fetched and may advance only through a fast-forward merge on their checked-out default branch. Dirty trees, other branches, detached HEADs, archived repositories, origin mismatches, path conflicts, and removed or inaccessible repositories are reported without destructive changes. Only repositories with changed HEAD or relevant metadata are analyzed. See [`docs/GITHUB-SYNC.md`](docs/GITHUB-SYNC.md).

## Portfolio-wide reporting

Portfolio OS `0.8.0` turns the synchronized workspace into deterministic portfolio artifacts:

```bash
portfolio-report --pretty
portfolio-report --workspace ~/Portfolio-OS-workspace --output-dir reports/latest
```

The pipeline writes `portfolio-summary.json`, `portfolio-report.md`, and `portfolio-graph.json`. Reports include analysis coverage, languages, frameworks, findings, repository status, and explicit attention queues for dirty, inaccessible, archived, missing-analysis, and analyzer-error cases. See [`docs/PORTFOLIO-REPORTING.md`](docs/PORTFOLIO-REPORTING.md).

## Portfolio history and change tracking

Portfolio OS `0.9.0` records an immutable snapshot after each report and compares it with the previous snapshot.

```bash
portfolio-report --pretty
portfolio-report --no-history
```

History records stable repository additions, removals, renames and metadata changes, HEAD movement, analysis metric changes, and portfolio summary deltas. Snapshot fingerprints are deterministic and history artifacts are persisted atomically. See [`docs/PORTFOLIO-HISTORY.md`](docs/PORTFOLIO-HISTORY.md).

## Portfolio trends and retention

Portfolio OS `0.10.0` analyzes all retained snapshots to produce multi-period trends and regression signals.

```bash
portfolio-trends --pretty
portfolio-trends --limit 30
portfolio-trends --retain 90 --pretty
portfolio-trends --retain 90 --apply-retention --pretty
```

Trend artifacts include metric timelines, net change, repository activity, and evidence-based regression signals. Snapshot retention is preview-only unless `--apply-retention` is supplied. See [`docs/PORTFOLIO-TRENDS.md`](docs/PORTFOLIO-TRENDS.md).

## Static portfolio dashboard

Portfolio OS `0.11.0` generates a self-contained dashboard from real portfolio and trend artifacts.

```bash
portfolio-dashboard --pretty
portfolio-dashboard --workspace ~/Portfolio-OS-workspace --output-dir public
```

The dashboard contains portfolio metrics, inline SVG trend visualization, languages, regression signals, attention queues, and repository status. It has no external scripts, fonts, trackers, network calls, or mock data. See [`docs/PORTFOLIO-DASHBOARD.md`](docs/PORTFOLIO-DASHBOARD.md).

## End-to-end refresh pipeline

Portfolio OS `0.12.0` runs synchronization, reporting, history, trends and dashboard generation through one command:

```bash
portfolio-refresh --pretty
portfolio-refresh --skip-sync --pretty
```

The refresh pipeline uses an exclusive workspace lock, records per-stage status and duration, blocks dependent stages after failure by default, and writes a durable run report to `<workspace>/pipeline/latest-run.json`. Best-effort continuation requires explicit `--continue-on-error`. See [`docs/REFRESH-PIPELINE.md`](docs/REFRESH-PIPELINE.md).

## Portfolio health policies

Portfolio OS `0.13.0` evaluates generated evidence against explicit fail and warning thresholds.

```bash
portfolio-policy --pretty
portfolio-policy --policy portfolio-policy.example.json --pretty
```

Supported gates include analysis coverage, dirty and inaccessible repositories, analyzer errors, finding totals, regression count, history depth, and pipeline completion. Failed rules return exit code `2`; warnings remain visible without failing the command. See [`docs/PORTFOLIO-POLICY.md`](docs/PORTFOLIO-POLICY.md).

## Production foundation

Typed runtime configuration, structured logging, and a stable analyzer plugin registry are available throughout the package.

```bash
cp portfolio-os.example.json portfolio-os.json
python -m portfolio_os.cli --runtime-config portfolio-os.json analyze . --pretty
python -m portfolio_os.cli --json-logs --log-level DEBUG analyze . --pretty
python -m portfolio_os.cli plugins
```

External analyzer packages can register through the `portfolio_os.analyzers` Python entry-point group. See [`docs/PRODUCTION-FOUNDATION.md`](docs/PRODUCTION-FOUNDATION.md).

## Governance commands

```bash
python -m portfolio_os.cli inventory
python -m portfolio_os.cli decisions
python -m portfolio_os.cli archive-candidates
```

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
- Existing README hero banners are preserved during regeneration.
- Automated README changes are based on source-code evidence.
- README replacement requires explicit `--write`.
- DNA similarity is review evidence, not an automatic merge decision.
- Analyzer plugins are read-only by contract unless a separate explicit execution workflow authorizes changes.
- GitHub synchronization never resets, rebases, cleans, force-updates, deletes branches, or deletes local repositories.
- Dirty working trees and non-default branches are preserved and reported.
- Portfolio artifacts are rebuilt from synchronization state and cached analyzer evidence, not repository marketing claims.
- Historical snapshots contain derived evidence only and never modify synchronized repositories.
- Snapshot deletion requires an explicit retention apply flag and always preserves at least one snapshot.
- Dashboard generation reads derived artifacts and writes only static output files.
- Concurrent refreshes are rejected through an exclusive workspace lock.
- Policy evaluation reads generated evidence and writes only a derived policy report.

Portfolio-level decisions live under [`docs/`](docs/), with the machine-readable inventory in [`config/portfolio.json`](config/portfolio.json).
