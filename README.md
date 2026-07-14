# Portfolio OS

Private governance and automation for the `benclawbot` GitHub portfolio.

Portfolio OS inventories repositories, analyzes implementation evidence, generates code-derived documentation, compares repository DNA, builds an explainable portfolio knowledge graph, and safely synchronizes a managed local workspace. Destructive portfolio actions remain disabled by default.

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

Portfolio-level decisions live under [`docs/`](docs/), with the machine-readable inventory in [`config/portfolio.json`](config/portfolio.json).
