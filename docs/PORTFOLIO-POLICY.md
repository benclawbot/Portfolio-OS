# Portfolio health policies

Portfolio OS converts generated portfolio evidence into explicit CI gates.

```bash
portfolio-policy --pretty
portfolio-policy --policy portfolio-policy.example.json --pretty
portfolio-refresh --skip-sync --policy portfolio-policy.example.json --pretty
```

The evaluator writes `<workspace>/policy/latest-policy.json`.

## Portfolio rules

- `min_analysis_coverage`
- `max_dirty_count`
- `max_inaccessible_count`
- `max_analysis_errors`
- `max_total_findings`
- `max_regressions`
- `min_history_snapshots`
- `require_pipeline_completed`

## Repository-specific rules

Policies may target repositories by exact `owner/name`:

- `require_analysis`
- `require_accessible`
- `allow_dirty`
- `min_test_files`
- `max_findings`
- `max_analysis_errors`

```json
{
  "repositories": {
    "benclawbot/example-project": {
      "require_analysis": {"value": true, "level": "fail"},
      "min_test_files": {"value": 1, "level": "warn"}
    }
  }
}
```

A missing repository policy target is a fail-level violation because the requested governance target cannot be evaluated.

## Rule schema

Each rule accepts exactly:

```json
{"value": 0, "level": "fail", "enabled": true}
```

Levels are `fail` or `warn`. Numeric rules require numeric values and boolean rules require booleans. Unknown sections, rules, or fields are rejected rather than ignored.

Warning violations are reported but do not fail the command. Any fail-level violation returns exit code `2`.

## Pipeline integration

Use `--enforce-policy` for built-in defaults, or `--policy` to automatically enable and enforce a supplied policy as the final refresh stage:

```bash
portfolio-refresh --skip-sync --enforce-policy --pretty
portfolio-refresh --skip-sync --policy portfolio-policy.example.json --pretty
```

The policy stage evaluates the current refresh as completed, avoiding dependence on a previous `latest-run.json`. A failed policy writes its policy report and marks the refresh pipeline failed.

Policy evaluation never modifies synchronized repositories or source artifacts.
