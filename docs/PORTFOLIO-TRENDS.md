# Portfolio trends and snapshot retention

Portfolio OS can analyze the complete snapshot history instead of comparing only the latest two runs.

```bash
portfolio-trends --pretty
portfolio-trends --limit 12
```

The command writes:

```text
<workspace>/trends/
├── portfolio-trends.json
└── portfolio-trends.md
```

## Trend model

The trend timeline includes repository, active, archived, inaccessible, dirty and analyzed counts, analysis coverage, files, tests, findings and analyzer errors.

Repository activity records:

- first and last appearance in the selected history window;
- number of default-branch HEAD changes;
- cumulative finding-count change;
- cumulative detected-test-file change.

Regression signals are evidence-based metric movements:

- analysis coverage decreased;
- dirty repository count increased;
- inaccessible repository count increased;
- analyzer errors increased;
- total findings increased.

These are signals for review, not automatic conclusions about project quality.

## Limiting analysis

Use only the latest number of snapshots:

```bash
portfolio-trends --limit 30
```

The history files remain unchanged. The limit affects only the generated trend artifacts.

## Snapshot retention

Retention is preview-only by default:

```bash
portfolio-trends --retain 90 --pretty
```

Apply the exact plan explicitly:

```bash
portfolio-trends --retain 90 --apply-retention --pretty
```

At least one snapshot must be retained. Files are selected oldest-first by their deterministic snapshot filenames. `latest.json` and `latest-delta.json` are not removed by retention.

Retention is the only destructive operation in this phase and requires the explicit `--apply-retention` flag.
