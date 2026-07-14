# Portfolio-wide reporting

After GitHub synchronization has populated the managed workspace, Portfolio OS can aggregate cached repository analyses and rebuild portfolio artifacts.

```bash
portfolio-report --pretty
portfolio-report --workspace ~/Portfolio-OS-workspace
portfolio-report --output-dir reports/latest --threshold 0.60
```

Equivalent module invocation:

```bash
python -m portfolio_os.portfolio_cli --pretty
```

## Generated artifacts

The command writes three deterministic artifacts:

- `portfolio-summary.json`: machine-readable portfolio inventory, analysis coverage, language and framework counts, findings, and attention queues.
- `portfolio-report.md`: human-readable portfolio overview and repository status report.
- `portfolio-graph.json`: rebuilt repository knowledge graph and similarity relationships.

The default destination is `<workspace>/portfolio/`. All summary and report writes use temporary files, `fsync`, and atomic replacement.

## Evidence model

Portfolio reporting consumes the synchronization state and cached analysis files under `<workspace>/analysis/<repository-id>.json`. It does not infer implementation claims from repository descriptions or README prose.

The report records:

- active, archived, inaccessible, and dirty repository counts;
- cached-analysis coverage;
- analyzed file and test-file totals;
- finding and analyzer-error totals;
- primary-language and detected-framework distribution;
- dirty, inaccessible, archived, missing-analysis, and analysis-error attention queues;
- repository-level synchronization and analysis evidence.

Invalid or unreadable cached analysis is reported on the repository record and treated as missing analysis rather than crashing the complete portfolio build.

## Graph eligibility

A repository is included in the rebuilt graph only when it is accessible, not archived, not dirty, exists locally, and contains a `.git` directory. Excluded repositories remain present in the summary and report.

The similarity threshold defaults to `0.55` and can be overridden with `--threshold`.
