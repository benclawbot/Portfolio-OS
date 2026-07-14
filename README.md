# Portfolio OS

Private, evidence-based governance and automation for the `benclawbot` GitHub portfolio.

Portfolio OS 1.0 safely synchronizes repositories, indexes GitHub metadata, analyzes implementation evidence, generates documentation, compares repository DNA, builds a knowledge graph, tracks portfolio history and trends, renders an offline dashboard, enforces health policies, records refresh runs, diagnoses locks, and validates persisted workspace artifacts.

## Primary workflow

```bash
export GITHUB_TOKEN=github_pat_...
portfolio-refresh --policy portfolio-policy.example.json --pretty
portfolio-workspace validate --pretty
```

The refresh pipeline runs:

1. safe GitHub synchronization and changed-repository analysis;
2. incremental branch, tag, release, issue, pull-request, status and check indexing;
3. portfolio report and knowledge graph generation;
4. immutable history snapshot and delta generation;
5. multi-period trend analysis;
6. offline dashboard generation;
7. optional policy enforcement.

Every run is protected by an exclusive workspace lock and recorded under `<workspace>/pipeline/runs/`.

## Commands

```bash
portfolio-os --help
portfolio-github-index --pretty
portfolio-report --pretty
portfolio-trends --pretty
portfolio-dashboard --pretty
portfolio-refresh --pretty
portfolio-policy --pretty
portfolio-ops runs --pretty
portfolio-ops lock-status --pretty
portfolio-workspace validate --pretty
portfolio-workspace repair-plan --pretty
```

## Repository analysis and documentation

```bash
python -m portfolio_os.cli analyze /path/to/repository --pretty
python -m portfolio_os.cli readme /path/to/repository --diff
python -m portfolio_os.cli readme /path/to/repository --write
python -m portfolio_os.cli dna /path/to/repository
python -m portfolio_os.cli compare /path/to/repo-a /path/to/repo-b --pretty
```

README generation is based on implementation evidence and preserves the existing leading hero banner.

## Safe synchronization

Missing repositories are cloned. Existing clean repositories may advance only through a fast-forward update on their checked-out default branch.

Portfolio OS never automatically:

- resets, rebases, or cleans a repository;
- force-updates a branch;
- deletes branches or local repositories;
- overwrites dirty working trees;
- switches non-default branches.

Dirty trees, detached HEADs, other branches, archived repositories, origin mismatches, path conflicts, and inaccessible repositories are preserved and reported.

## GitHub metadata index

Each refresh writes a portfolio manifest to `<workspace>/github/index.json` and one normalized artifact per repository under `<workspace>/github/repositories/`.

Indexed data includes:

- branches and protection state;
- tags and releases;
- issues and labels;
- pull requests and branch relationships;
- combined commit status and check runs for the default-branch head.

The index fingerprint uses repository identity, default branch, head SHA, update timestamp, archive state and accessibility. Unchanged repository artifacts are reused. Use `portfolio-github-index --force` or `portfolio-refresh --force-github-index` for a complete rebuild. Indexing never changes managed checkouts.

## Reports and dashboard

Derived artifacts include:

```text
github/        normalized GitHub metadata and incremental index manifest
portfolio/     summary, Markdown report, knowledge graph
history/       immutable snapshots and latest delta
trends/        timelines, net changes, regressions, repository activity
dashboard/     self-contained HTML and exact dashboard data
pipeline/      latest run and immutable run history
policy/        latest policy evaluation
workspace/     validation manifest and artifact digests
```

The dashboard has no external scripts, fonts, trackers, CDN assets, or network requests. It displays repository state, trends, policy violations, and recent refresh history.

## Policies

```bash
portfolio-policy --policy portfolio-policy.example.json --pretty
portfolio-refresh --policy portfolio-policy.example.json --pretty
```

Policies support portfolio-wide thresholds and exact repository-specific rules. Unknown sections, rules, fields, and invalid threshold types fail clearly. Fail-level violations return exit code `2`; warnings remain visible without failing the command.

## Operations and recovery

```bash
portfolio-ops runs --limit 10 --pretty
portfolio-ops lock-status --stale-after 3600 --pretty
portfolio-ops clear-stale-lock --stale-after 3600 --pretty
portfolio-workspace repair-plan --pretty
```

Stale-lock cleanup is explicit and refuses to remove a lock that has not met the configured staleness threshold. Workspace repair planning is non-destructive and maps missing or invalid artifacts to the minimum rebuild stages.

## Development and release verification

```bash
python -m pip install -e ".[dev]"
python -m compileall -q portfolio_os
python -m ruff check portfolio_os tests
python -m pyright portfolio_os
python -m pytest -q --cov=portfolio_os --cov-branch --cov-report=term-missing --cov-fail-under=90
python -m build
```

Stable releases are produced by the GitHub Actions **Release** workflow. It verifies the version, reruns compilation, linting, type checking and tests, builds and reinstalls the wheel, generates SHA-256 checksums, creates an annotated tag, and publishes the GitHub Release. See [`docs/RELEASING.md`](docs/RELEASING.md).

## Documentation

- [`docs/ANALYSIS-ENGINE.md`](docs/ANALYSIS-ENGINE.md)
- [`docs/README-GENERATOR.md`](docs/README-GENERATOR.md)
- [`docs/REPOSITORY-DNA.md`](docs/REPOSITORY-DNA.md)
- [`docs/KNOWLEDGE-GRAPH.md`](docs/KNOWLEDGE-GRAPH.md)
- [`docs/GITHUB-SYNC.md`](docs/GITHUB-SYNC.md)
- [`docs/PORTFOLIO-REPORTING.md`](docs/PORTFOLIO-REPORTING.md)
- [`docs/PORTFOLIO-HISTORY.md`](docs/PORTFOLIO-HISTORY.md)
- [`docs/PORTFOLIO-TRENDS.md`](docs/PORTFOLIO-TRENDS.md)
- [`docs/PORTFOLIO-DASHBOARD.md`](docs/PORTFOLIO-DASHBOARD.md)
- [`docs/REFRESH-PIPELINE.md`](docs/REFRESH-PIPELINE.md)
- [`docs/PORTFOLIO-POLICY.md`](docs/PORTFOLIO-POLICY.md)
- [`docs/OPERATIONS-AND-VALIDATION.md`](docs/OPERATIONS-AND-VALIDATION.md)
- [`docs/RELEASING.md`](docs/RELEASING.md)
- [`CHANGELOG.md`](CHANGELOG.md)

Portfolio-level decisions remain under [`docs/`](docs/), with the machine-readable inventory in [`config/portfolio.json`](config/portfolio.json).
