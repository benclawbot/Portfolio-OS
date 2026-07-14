# Changelog

## 1.0.0

Portfolio OS reaches its first stable release with an end-to-end, evidence-based portfolio governance workflow.

### Core capabilities

- safe GitHub repository discovery and managed workspace synchronization;
- changed-repository analysis with structured cached evidence;
- evidence-derived README generation with hero-banner preservation;
- repository DNA comparison and explainable portfolio knowledge graph;
- portfolio summary, Markdown report, graph, immutable history, deltas and trends;
- self-contained offline dashboard with repository, trend, policy and refresh-run visibility;
- locked end-to-end refresh pipeline with durable stage results;
- strict portfolio and repository health policies with CI exit codes;
- immutable refresh-run history and stale-lock diagnostics;
- workspace artifact validation, SHA-256 manifest and repair-stage planning;
- analyzer plugin entry point and typed runtime configuration.

### Stability contract

- no reset, rebase, clean, forced update, branch deletion or local repository deletion;
- dirty working trees and non-default branches remain preserved;
- destructive retention requires explicit apply flags;
- policy evaluation and dashboard generation modify only derived artifacts;
- public JSON artifacts include explicit schema versions where introduced in the stable release line;
- console commands and exported Python APIs follow semantic versioning from this release.

### Known limits

- GitHub synchronization requires a token for private repositories;
- stale-lock detection is age-based and does not yet verify cross-platform PID identity;
- repository policy selectors require exact `owner/name` values;
- the static dashboard intentionally has no client-side JavaScript;
- schema migrations for pre-1.0 experimental artifacts are not automatic.
