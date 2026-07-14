# API, jobs and artifact management

Portfolio OS exposes the same persisted capabilities through a stable Python API, a localhost REST service and a durable filesystem job queue.

## Python API

Public classes are exported from `portfolio_os` and follow semantic versioning. Core entry points include:

- `PortfolioBuilder`;
- `PortfolioPipeline`;
- `GitHubMetadataIndexer`;
- `RepositoryIntelligence`;
- `PortfolioBacklog`;
- `PortfolioReuseAnalyzer`;
- `RepositoryLineage`;
- `PortfolioDocumentGenerator`;
- `ArtifactManager`;
- `JobQueue`;
- `PortfolioService`.

## Local REST service

The service binds to localhost by default and has no external dependencies.

```bash
portfolio-service --workspace ~/.portfolio-os serve --host 127.0.0.1 --port 8765
```

Versioned endpoints:

```text
GET  /v1/health
GET  /v1/jobs
GET  /v1/jobs/{id}
POST /v1/jobs
POST /v1/jobs/run-next
GET  /v1/artifacts?path=<workspace-relative-path>
GET  /v1/artifacts/catalog
GET  /v1/artifacts/{artifact-id}
```

The service prevents artifact paths from escaping the configured workspace and limits request bodies to one megabyte.

## Durable jobs

Supported job kinds:

- `report`;
- `backlog`;
- `trends`;
- `documents`;
- `artifacts`.

Job records move atomically through:

```text
<workspace>/jobs/pending/
<workspace>/jobs/running/
<workspace>/jobs/completed/
<workspace>/jobs/failed/
```

Each record includes a stable ID, timestamps, parameters, status, result or error. A process interruption leaves inspectable state rather than losing the request.

```bash
portfolio-service --workspace ~/.portfolio-os jobs
portfolio-service --workspace ~/.portfolio-os run-next
```

## Artifact catalog

The artifact manager catalogs generated outputs with:

- deterministic artifact ID;
- workspace-relative path;
- category and content type;
- byte size;
- SHA-256 digest;
- modification timestamp.

```bash
portfolio-artifacts --workspace ~/.portfolio-os catalog
portfolio-artifacts --workspace ~/.portfolio-os resolve <artifact-id>
```

## Retention safety

Retention is plan-first and explicitly destructive only after confirmation.

```bash
portfolio-artifacts --workspace ~/.portfolio-os retention-plan \
  --keep-history 30 --keep-runs 100 > retention.json

portfolio-artifacts --workspace ~/.portfolio-os apply-retention \
  retention.json --confirm
```

Only immutable history snapshots and refresh-run records are eligible. Repository checkouts, current reports and source files are never deleted by artifact retention.

## Telemetry

Portfolio OS writes local-only operational metrics to:

```text
<workspace>/telemetry/metrics.json
```

The telemetry contains run counts, success rates, stage failure counts and timing summaries. It does not export data over the network or include repository source code.
