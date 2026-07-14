# End-to-end refresh pipeline

Portfolio OS can run synchronization and all derived artifact stages through one command:

```bash
portfolio-refresh --pretty
```

The ordered stages are:

1. GitHub synchronization and changed-repository analysis;
2. portfolio report and knowledge graph generation;
3. immutable history snapshot and latest delta;
4. multi-snapshot trend generation;
5. static dashboard generation.

## Existing workspace mode

Build all derived artifacts without contacting GitHub:

```bash
portfolio-refresh --skip-sync --pretty
```

This is useful for CI, offline work, or rebuilding reports from an existing synchronization state and analysis cache.

## Failure behavior

By default, a failed stage blocks every later stage because their inputs may be incomplete:

```text
sync: failed
report: blocked
trends: blocked
dashboard: blocked
```

Use explicit best-effort continuation when existing artifacts may still support later stages:

```bash
portfolio-refresh --continue-on-error --pretty
```

The overall run remains failed when any stage fails, even if later stages complete.

## Concurrency lock

The pipeline creates `<workspace>/.portfolio-os-refresh.lock` using exclusive file creation. A second refresh exits without running while the lock exists. The lock is removed after success or handled stage failure.

An abandoned lock from a forcibly terminated process must be reviewed before manual removal. The lock file contains the process ID and start epoch for diagnosis.

## Durable run report

Every completed orchestration attempt writes:

```text
<workspace>/pipeline/latest-run.json
```

The report contains:

- overall status and duration;
- ordered stage statuses;
- per-stage durations;
- generated artifact paths and stage summaries;
- normalized stage errors;
- skipped and blocked stages.

The report is written atomically after all stage handling is complete.

## Options

```bash
portfolio-refresh --owner benclawbot
portfolio-refresh --no-analyze
portfolio-refresh --threshold 0.60
portfolio-refresh --trend-limit 30
portfolio-refresh --skip-sync
portfolio-refresh --continue-on-error
```

Synchronization retains all existing safety constraints: no reset, rebase, clean, forced update, branch deletion or local repository deletion.
