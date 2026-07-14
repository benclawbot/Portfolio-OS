# Operations, recovery, and workspace validation

Portfolio OS 1.0 records every completed refresh attempt under:

```text
<workspace>/pipeline/
├── latest-run.json
└── runs/<timestamp>-<status>.json
```

List recent runs:

```bash
portfolio-ops runs --pretty
portfolio-ops runs --limit 5 --pretty
```

## Lock diagnostics

Inspect the refresh lock without modifying it:

```bash
portfolio-ops lock-status --pretty
portfolio-ops lock-status --stale-after 7200 --pretty
```

A lock is considered stale when its recorded age meets the configured threshold or its JSON content is malformed. Cleanup is always an explicit command:

```bash
portfolio-ops clear-stale-lock --stale-after 7200 --pretty
```

A non-stale lock is never removed by this command.

## Workspace validation

Validate required derived artifacts and write a SHA-256 manifest:

```bash
portfolio-workspace validate --pretty
```

The validator checks required presence, readability, JSON object shape where applicable, byte size, and digest. The manifest is written to:

```text
<workspace>/workspace/manifest.json
```

Optional pipeline and policy artifacts produce warnings when absent. Missing or invalid core artifacts fail validation.

## Repair planning

Generate a non-destructive stage plan:

```bash
portfolio-workspace repair-plan --pretty
```

The plan maps invalid artifacts to the minimum rebuild stages: `sync`, `report`, `trends`, and `dashboard`. It does not execute those stages or modify repositories.

A typical recovery sequence is:

```bash
portfolio-workspace repair-plan --pretty
portfolio-refresh --skip-sync --enforce-policy --pretty
portfolio-workspace validate --pretty
```

Run synchronization instead of `--skip-sync` when the plan includes `sync`.
