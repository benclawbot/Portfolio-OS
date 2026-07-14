# Portfolio OS

Private governance and automation for the `benclawbot` GitHub portfolio.

Portfolio OS inventories repositories, analyzes implementation evidence, records portfolio decisions, and generates code-derived documentation. Destructive portfolio actions remain disabled by default.

## Phase 1: repository analysis

Analyze any local repository checkout and emit structured JSON covering:

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

See [`docs/ANALYSIS-ENGINE.md`](docs/ANALYSIS-ENGINE.md).

## Phase 2: evidence-based README generation

Generate deterministic documentation from Phase 1 evidence while preserving the existing leading hero banner:

```bash
# Preview
python -m portfolio_os.cli readme /path/to/repository

# Review changes
python -m portfolio_os.cli readme /path/to/repository --diff

# Detect README drift in CI
python -m portfolio_os.cli readme /path/to/repository --check

# Replace README.md atomically
python -m portfolio_os.cli readme /path/to/repository --write
```

Generation stops if an analyzer fails. Existing README body claims are not treated as implementation evidence. See [`docs/README-GENERATOR.md`](docs/README-GENERATOR.md).

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
- Existing README hero banners are preserved during regeneration.
- Automated README changes are based on source-code evidence.
- README replacement requires explicit `--write`.

Portfolio-level decisions live under [`docs/`](docs/), with the machine-readable inventory in [`config/portfolio.json`](config/portfolio.json).
