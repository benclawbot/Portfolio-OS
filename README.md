# Portfolio OS

Private governance and automation for the `benclawbot` GitHub portfolio.

Portfolio OS inventories repositories, analyzes implementation evidence, records portfolio decisions, and will orchestrate code-derived documentation and portfolio-wide improvements. Destructive actions remain disabled by default.

## Phase 1: repository analysis

The first production capability analyzes any local repository checkout and emits structured JSON covering:

- repository structure and entry points,
- languages and frameworks,
- manifests, lockfiles, dependencies, and commands,
- tests and GitHub Actions workflows,
- documentation and governance completeness,
- TODO/FIXME markers,
- basic secret-pattern and `.gitignore` checks,
- evidence-backed findings with severity and confidence.

```bash
python -m portfolio_os.cli analyze /path/to/repository --pretty
python -m portfolio_os.cli analyze /path/to/repository \
  --output reports/latest/repository.json
```

See [`docs/ANALYSIS-ENGINE.md`](docs/ANALYSIS-ENGINE.md) for the output contract and current limitations.

## Governance commands

```bash
python -m portfolio_os.cli inventory
python -m portfolio_os.cli decisions
python -m portfolio_os.cli archive-candidates
```

## Development

```bash
python -m pytest -q
python -m portfolio_os.cli analyze tests/fixtures/sample_repo --pretty
```

## Safety defaults

- Archive actions are recommendation-only.
- Pull-request actions are analysis-only.
- Existing README hero banners must be preserved during future regeneration.
- Automated README changes will be based on source-code evidence.

Portfolio-level decisions live under [`docs/`](docs/), with the machine-readable inventory in [`config/portfolio.json`](config/portfolio.json).
