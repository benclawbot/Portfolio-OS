# Repository Analysis Engine

Portfolio OS Phase 1 analyzes a local repository checkout and emits structured JSON suitable for reports, automation, and future Medusa integration.

## Current analyzers

- Repository structure, file counts, entry points, and TODO/FIXME markers
- Languages and representative files
- Package manifests, lockfiles, dependencies, scripts, and frameworks
- Conventional tests and GitHub Actions workflows
- README and governance-document completeness
- High-confidence secret-pattern screening and `.gitignore` presence

Each analyzer returns facts and evidence-backed findings. Analyzer failures are isolated and recorded instead of aborting the scan.

## Usage

```bash
python -m portfolio_os.cli analyze /path/to/repository --pretty
python -m portfolio_os.cli analyze /path/to/repository --output reports/latest/repository.json
```

The command exits non-zero only when an analyzer itself fails. Findings do not make the scan command fail.

## Output contract

The JSON report includes:

- repository identity and scan timestamp,
- facts grouped by analyzer,
- findings with severity, confidence, evidence, and recommendations,
- isolated analyzer errors,
- aggregate severity counts.

## Intentional limitations

Phase 1 does not yet clone repositories, call GitHub APIs, calculate semantic duplication, execute project tests, measure coverage, or alter any repository. Those capabilities build on this stable local analysis contract.
