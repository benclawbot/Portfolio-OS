# Portfolio OS

Private governance and automation for the `benclawbot` GitHub portfolio.

Portfolio OS inventories repositories, analyzes implementation evidence, generates code-derived documentation, and compares repository DNA. Destructive portfolio actions remain disabled by default.

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
python -m portfolio_os.cli readme /path/to/repository
python -m portfolio_os.cli readme /path/to/repository --diff
python -m portfolio_os.cli readme /path/to/repository --check
python -m portfolio_os.cli readme /path/to/repository --write
```

Generation stops if an analyzer fails. Existing README body claims are not treated as implementation evidence. See [`docs/README-GENERATOR.md`](docs/README-GENERATOR.md).

## Phase 3: repository DNA

Generate a deterministic repository fingerprint:

```bash
python -m portfolio_os.cli dna /path/to/repository
```

Compare two repositories with weighted, explainable overlap scoring:

```bash
python -m portfolio_os.cli compare /path/to/repo-a /path/to/repo-b --pretty
```

Similarity output includes per-dimension overlap, unique evidence on each side, and human-readable reasons. See [`docs/REPOSITORY-DNA.md`](docs/REPOSITORY-DNA.md).

## Governance commands

```bash
python -m portfolio_os.cli inventory
python -m portfolio_os.cli decisions
python -m portfolio_os.cli archive-candidates
```

## Development

```bash
python -m compileall -q portfolio_os
python -m pytest -q
python -m portfolio_os.cli compare tests/fixtures/sample_repo tests/fixtures/sample_repo --pretty
```

## Safety defaults

- Archive actions are recommendation-only.
- Pull-request actions are analysis-only.
- Existing README hero banners are preserved during regeneration.
- Automated README changes are based on source-code evidence.
- README replacement requires explicit `--write`.
- DNA similarity is review evidence, not an automatic merge decision.

Portfolio-level decisions live under [`docs/`](docs/), with the machine-readable inventory in [`config/portfolio.json`](config/portfolio.json).
