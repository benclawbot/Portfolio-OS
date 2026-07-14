# Intelligence and self-generated backlog

Portfolio OS converts persisted repository and GitHub evidence into explainable portfolio decisions. It does not use opaque model judgments or invented metrics.

## Repository scores

Each active repository receives four scores from 0 to 100:

- architecture quality;
- technical debt health;
- security posture;
- release readiness.

Every score includes:

- the starting baseline;
- positive and negative factors;
- the exact evidence supporting each factor;
- confidence based on evidence availability.

Missing analysis or GitHub metadata lowers confidence and creates explicit backlog work to restore evidence coverage.

## Duplicate components and shared libraries

The reuse analyzer scans source files in managed repositories, excluding generated, vendor, dependency and cache directories. Files are normalized for line endings and compared by SHA-256.

Only exact source matches appearing in at least two repositories are reported as duplicate component groups. The output includes every occurrence, line count, digest and a recommendation to consolidate the component into a shared library or template.

Artifacts:

```text
<workspace>/reuse/duplicate-components.json
<workspace>/reuse/shared-library-recommendations.md
```

## Repository lineage

The lineage builder translates explicit inventory decisions into typed relationships such as:

- `merge_into`;
- `migration_source_for`;
- `archive_candidate`;
- `reference_of`;
- `consolidate_with`;
- `superseded_by`.

Inbound and outbound impact indexes make it possible to identify repositories affected by a consolidation or migration decision.

Artifacts:

```text
<workspace>/lineage/repository-lineage.json
<workspace>/lineage/repository-lineage.md
```

## Prioritized backlog

The backlog generator creates durable recommendations from evidence gaps, workspace safety states and low intelligence scores.

Each item contains:

- stable deterministic ID;
- repository and category;
- evidence;
- expected impact;
- effort and risk estimates;
- confidence;
- calculated priority score;
- acceptance criteria;
- verification plan;
- lifecycle status.

Priority is impact adjusted by confidence, effort and risk. The generator never creates work without a traceable evidence source.

```bash
portfolio-backlog --pretty
```

Artifacts:

```text
<workspace>/backlog/portfolio-backlog.json
<workspace>/backlog/portfolio-backlog.md
```

The resulting loop is:

```text
synchronize and analyze
→ score portfolio evidence
→ detect reuse and lineage opportunities
→ generate prioritized backlog
→ implement selected work
→ verify through the next refresh
```
