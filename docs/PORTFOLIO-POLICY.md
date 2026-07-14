# Portfolio health policies

Portfolio OS can convert generated portfolio evidence into explicit CI gates.

```bash
portfolio-policy --pretty
portfolio-policy --policy portfolio-policy.example.json --pretty
```

The command reads the latest portfolio summary and, when available, trends and pipeline reports. It writes:

```text
<workspace>/policy/latest-policy.json
```

## Supported rules

- `min_analysis_coverage`
- `max_dirty_count`
- `max_inaccessible_count`
- `max_analysis_errors`
- `max_total_findings`
- `max_regressions`
- `min_history_snapshots`
- `require_pipeline_completed`

Each rule supports:

```json
{"value": 0, "level": "fail", "enabled": true}
```

Levels are `fail` or `warn`. Warning violations are reported but do not fail the command. Any failing violation returns exit code `2`.

## Default behavior

The built-in defaults are intentionally conservative: analyzer errors fail, while dirty repositories, inaccessible repositories, regressions, and insufficient history warn. Pipeline completion is not required unless explicitly enabled by policy.

## CI usage

```bash
portfolio-refresh --skip-sync --pretty
portfolio-policy --policy portfolio-policy.example.json --pretty
```

Policy reports include the expected condition, actual value, level, message, and aggregate failure/warning counts. Policy evaluation never modifies synchronized repositories or source artifacts.
