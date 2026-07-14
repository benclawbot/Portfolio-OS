# Portfolio history and change tracking

Every `portfolio-report` run records an immutable portfolio snapshot unless `--no-history` is supplied.

```bash
portfolio-report --pretty
portfolio-report --no-history
```

## History layout

```text
<workspace>/history/
├── latest.json
├── latest-delta.json
└── snapshots/
    └── <timestamp>-<fingerprint>.json
```

Snapshots contain the complete portfolio summary together with a SHA-256 fingerprint of its canonical JSON representation. Identical portfolio data receives the same fingerprint even when recorded at different times.

## Delta model

`latest-delta.json` compares the new snapshot with the previously recorded snapshot and reports:

- repositories added or removed by stable repository ID;
- repository field changes, including name, HEAD SHA, visibility, archived/accessibility/dirty state, primary language, file count, test count, findings, and analyzer errors;
- portfolio summary changes with numeric before, after, and change values;
- whether the snapshot is the first baseline.

The first snapshot treats all current repositories as additions. Later unchanged snapshots produce zero added, removed, and changed counts.

## Persistence and safety

Snapshot, latest, and delta files are written through temporary files, flushed with `fsync`, and atomically replaced where applicable. Historical snapshot files are never mutated by later runs.

History contains derived metadata and analyzer evidence only. It does not alter synchronized repositories or perform Git operations.
