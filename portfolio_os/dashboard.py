from __future__ import annotations

import html
import json
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from portfolio_os.operations import RefreshOperations


@dataclass(frozen=True)
class DashboardResult:
    html_path: Path
    data_path: Path


class PortfolioDashboard:
    """Generate a self-contained static dashboard from Portfolio OS artifacts."""

    def __init__(self, workspace: Path, output_dir: Path | None = None) -> None:
        self.workspace = workspace.expanduser().resolve()
        self.output_dir = (output_dir or self.workspace / "dashboard").expanduser().resolve()
        self.summary_path = self.workspace / "portfolio" / "portfolio-summary.json"
        self.trends_path = self.workspace / "trends" / "portfolio-trends.json"
        self.policy_path = self.workspace / "policy" / "latest-policy.json"
        self.backlog_path = self.workspace / "backlog" / "portfolio-backlog.json"
        self.reuse_path = self.workspace / "reuse" / "duplicate-components.json"
        self.lineage_path = self.workspace / "lineage" / "repository-lineage.json"

    def build(self) -> DashboardResult:
        portfolio = self._read_json(self.summary_path)
        trends = self._read_json(self.trends_path, required=False) or self._empty_trends()
        policy = self._read_json(self.policy_path, required=False) or self._empty_policy()
        backlog = self._read_json(self.backlog_path, required=False) or {"summary": {"item_count": 0}, "items": []}
        reuse = self._read_json(self.reuse_path, required=False) or {"summary": {"duplicate_group_count": 0}, "groups": []}
        lineage = self._read_json(self.lineage_path, required=False) or {"summary": {"edge_count": 0}, "edges": []}
        runs = RefreshOperations(self.workspace).list_runs(limit=10)
        payload = {
            "portfolio": portfolio,
            "trends": trends,
            "policy": policy,
            "backlog": backlog,
            "reuse": reuse,
            "lineage": lineage,
            "runs": runs,
        }
        data_path = self.output_dir / "dashboard-data.json"
        html_path = self.output_dir / "index.html"
        self._write_text_atomic(data_path, json.dumps(payload, indent=2, sort_keys=True) + "\n")
        self._write_text_atomic(html_path, self._render(payload))
        return DashboardResult(html_path, data_path)

    @staticmethod
    def _read_json(path: Path, required: bool = True) -> dict[str, Any] | None:
        if not path.exists():
            if required:
                raise FileNotFoundError(f"required artifact not found: {path}")
            return None
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError(f"artifact must contain a JSON object: {path}")
        return data

    @staticmethod
    def _empty_trends() -> dict[str, Any]:
        return {
            "snapshot_count": 0,
            "period": {"start": None, "end": None},
            "timeline": [],
            "net_change": {},
            "regressions": [],
            "repository_activity": [],
        }

    @staticmethod
    def _empty_policy() -> dict[str, Any]:
        return {
            "status": "not-evaluated",
            "evaluated_rules": 0,
            "violations": [],
            "summary": {"failure_count": 0, "warning_count": 0},
        }

    @staticmethod
    def _write_text_atomic(path: Path, content: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
        temporary = Path(temporary_name)
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
                handle.write(content)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, path)
        finally:
            temporary.unlink(missing_ok=True)

    @staticmethod
    def _bars(values: dict[str, Any]) -> str:
        if not values:
            return '<p class="muted">No language evidence available.</p>'
        maximum = max(int(value) for value in values.values()) or 1
        rows = []
        for label, raw_value in values.items():
            value = int(raw_value)
            width = max(2, round(value / maximum * 100))
            rows.append(
                f'<div class="bar"><span>{html.escape(str(label))}</span>'
                f'<div class="track"><div class="fill" style="width:{width}%"></div></div>'
                f'<strong>{value}</strong></div>'
            )
        return "".join(rows)

    @staticmethod
    def _line_chart(timeline: list[dict[str, Any]], metric: str) -> str:
        values = [float(item.get("metrics", {}).get(metric, 0) or 0) for item in timeline]
        if not values:
            return '<p class="muted">No historical snapshots available.</p>'
        width, height, padding = 720, 220, 28
        minimum, maximum = min(values), max(values)
        span = maximum - minimum or 1.0
        denominator = max(len(values) - 1, 1)
        points = []
        for index, value in enumerate(values):
            x = padding + (width - 2 * padding) * index / denominator
            y = height - padding - (height - 2 * padding) * (value - minimum) / span
            points.append(f"{x:.1f},{y:.1f}")
        circles = "".join(
            f'<circle cx="{point.split(",")[0]}" cy="{point.split(",")[1]}" r="4" class="dot"/>'
            for point in points
        )
        return (
            f'<svg viewBox="0 0 {width} {height}" role="img" aria-label="{html.escape(metric)} trend">'
            f'<line x1="{padding}" y1="{height-padding}" x2="{width-padding}" y2="{height-padding}" class="axis"/>'
            f'<polyline points="{" ".join(points)}" class="trend-line"/>{circles}</svg>'
        )

    @staticmethod
    def _repository_row(item: dict[str, Any]) -> str:
        intelligence = item.get("intelligence", {}).get("overall_score", "n/a")
        return (
            "<tr>"
            f'<td><strong>{html.escape(str(item.get("full_name", "unknown")))}</strong></td>'
            f'<td><span class="status">{html.escape(str(item.get("sync_status", "unknown")))}</span></td>'
            f'<td>{html.escape(str(item.get("primary_language") or "unknown"))}</td>'
            f'<td>{html.escape(str(item.get("test_file_count", 0)))}</td>'
            f'<td>{html.escape(str(item.get("finding_count", 0)))}</td>'
            f'<td>{html.escape(str(intelligence))}</td>'
            "</tr>"
        )

    @staticmethod
    def _policy_items(policy: dict[str, Any]) -> str:
        violations = policy.get("violations", [])
        if not violations:
            return '<li class="ok">No policy violations.</li>'
        return "".join(
            f'<li class="{html.escape(str(item.get("level", "warn")))}">'
            f'<strong>{html.escape(str(item.get("rule", "unknown")))}</strong>'
            f'{" — " + html.escape(str(item.get("repository"))) if item.get("repository") else ""}: '
            f'{html.escape(str(item.get("message", "")))}</li>'
            for item in violations
        )

    @staticmethod
    def _run_rows(runs: list[dict[str, Any]]) -> str:
        if not runs:
            return '<tr><td colspan="4" class="muted">No refresh history available.</td></tr>'
        rows = []
        for run in runs:
            failed = [stage.get("name") for stage in run.get("stages", []) if stage.get("status") == "failed"]
            rows.append(
                "<tr>"
                f'<td>{html.escape(str(run.get("status", "unknown")))}</td>'
                f'<td>{float(run.get("duration_seconds", 0) or 0):.3f}s</td>'
                f'<td>{html.escape(", ".join(str(item) for item in failed) or "none")}</td>'
                f'<td>{html.escape(Path(str(run.get("path", ""))).name)}</td>'
                "</tr>"
            )
        return "".join(rows)

    @staticmethod
    def _backlog_items(backlog: dict[str, Any]) -> str:
        items = backlog.get("items", [])[:10]
        if not items:
            return '<li class="ok">No evidence-backed work is currently recommended.</li>'
        return "".join(
            f'<li><strong>{html.escape(str(item.get("repository", "unknown")))}</strong> — '
            f'{html.escape(str(item.get("title", "")))} '
            f'<span class="muted">priority {html.escape(str(item.get("priority_score", 0)))}</span></li>'
            for item in items
        )

    def _render(self, payload: dict[str, Any]) -> str:
        portfolio = payload["portfolio"]
        trends = payload["trends"]
        policy = payload["policy"]
        backlog = payload["backlog"]
        reuse = payload["reuse"]
        lineage = payload["lineage"]
        runs = payload["runs"]
        summary = portfolio.get("summary", {})
        repositories = portfolio.get("repositories", [])
        attention = portfolio.get("attention", {})
        languages = portfolio.get("languages", {})
        timeline = trends.get("timeline", [])
        regressions = trends.get("regressions", [])
        policy_summary = policy.get("summary", {})

        cards = [
            ("Repositories", summary.get("repository_count", 0)),
            ("Intelligence", f"{float(summary.get('intelligence_score', 0) or 0):.1f}"),
            ("Analysis coverage", f"{summary.get('analysis_coverage', 0):.0%}"),
            ("Backlog", backlog.get("summary", {}).get("item_count", 0)),
            ("Duplicate groups", reuse.get("summary", {}).get("duplicate_group_count", 0)),
            ("Lineage edges", lineage.get("summary", {}).get("edge_count", 0)),
        ]
        card_html = "".join(
            f'<article class="card"><span>{html.escape(str(label))}</span><strong>{html.escape(str(value))}</strong></article>'
            for label, value in cards
        )
        regression_html = "".join(
            f'<li><strong>{html.escape(str(item.get("metric")))}</strong> '
            f'{html.escape(str(item.get("before")))} → {html.escape(str(item.get("after")))}</li>'
            for item in regressions
        ) or "<li>No regressions detected.</li>"
        attention_count = sum(len(value) for value in attention.values() if isinstance(value, list))
        attention_html = "".join(
            f'<li><strong>{html.escape(str(category).replace("_", " ").title())}:</strong> {len(values)}</li>'
            for category, values in attention.items()
            if isinstance(values, list)
        ) or "<li>No attention items.</li>"
        repository_rows = "".join(self._repository_row(item) for item in repositories)

        return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Portfolio OS Dashboard</title>
<style>
:root{{--bg:#f5f2eb;--panel:#fffdf8;--ink:#1f2328;--muted:#6f746f;--line:#ded8cc;--accent:#d97745;--danger:#9f3a38;--ok:#2f6f4e}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--ink);font:15px/1.5 system-ui,-apple-system,sans-serif}}main{{max-width:1400px;margin:auto;padding:28px}}
header{{display:flex;justify-content:space-between;gap:20px;align-items:end;margin-bottom:24px}}h1{{margin:0;font-size:36px;letter-spacing:-.04em}}h2{{margin:0 0 14px;font-size:18px}}
.sub,.muted,.meta{{color:var(--muted)}}.grid{{display:grid;grid-template-columns:repeat(6,1fr);gap:12px}}.layout{{display:grid;grid-template-columns:1.2fr .8fr;gap:16px;margin-top:16px}}
.card,.panel{{background:var(--panel);border:1px solid var(--line);border-radius:18px;box-shadow:0 12px 30px rgba(31,35,40,.05)}}.card{{padding:16px}}.card span{{display:block;color:var(--muted);font-size:12px;text-transform:uppercase;letter-spacing:.08em}}.card strong{{font-size:25px}}
.panel{{padding:20px}}.wide{{grid-column:1/-1}}.bar{{display:grid;grid-template-columns:110px 1fr 38px;gap:10px;align-items:center;margin:9px 0}}.track{{height:9px;background:#ebe5da;border-radius:99px;overflow:hidden}}.fill{{height:100%;background:var(--accent)}}
table{{width:100%;border-collapse:collapse}}th,td{{padding:11px 8px;border-bottom:1px solid var(--line);text-align:left;font-size:13px}}th{{color:var(--muted);font-weight:600}}.status{{display:inline-block;padding:2px 8px;border-radius:99px;background:#eee8dc}}ul{{margin:0;padding-left:18px}}li.fail{{color:var(--danger)}}li.warn{{color:#8a5b16}}li.ok{{color:var(--ok)}}
svg{{width:100%;height:220px;display:block}}.axis{{stroke:var(--line);stroke-width:1}}.trend-line{{fill:none;stroke:var(--accent);stroke-width:4;stroke-linecap:round;stroke-linejoin:round}}.dot{{fill:var(--panel);stroke:var(--accent);stroke-width:3}}.attention{{font-weight:700;color:var(--danger)}}
@media(max-width:900px){{.grid{{grid-template-columns:repeat(2,1fr)}}.layout{{grid-template-columns:1fr}}header{{display:block}}}}
</style></head><body><main>
<header><div><h1>Portfolio OS</h1><div class="sub">Evidence-based portfolio dashboard</div></div><div class="meta">Owner: {html.escape(str(portfolio.get('owner') or 'unknown'))}<br>Snapshots: {html.escape(str(trends.get('snapshot_count', 0)))}</div></header>
<section class="grid">{card_html}</section><section class="layout">
<article class="panel"><h2>Analysis coverage trend</h2>{self._line_chart(timeline, 'analysis_coverage')}</article>
<article class="panel"><h2>Languages</h2>{self._bars(languages)}</article>
<article class="panel"><h2>Regression signals</h2><ul>{regression_html}</ul></article>
<article class="panel"><h2>Attention queue <span class="attention">{attention_count}</span></h2><ul>{attention_html}</ul></article>
<article class="panel wide"><h2>Highest-priority backlog</h2><ul>{self._backlog_items(backlog)}</ul></article>
<article class="panel wide"><h2>Policy — {html.escape(str(policy.get('status', 'not-evaluated')))} · failures {policy_summary.get('failure_count', 0)} · warnings {policy_summary.get('warning_count', 0)}</h2><ul>{self._policy_items(policy)}</ul></article>
<article class="panel wide"><h2>Recent refresh runs</h2><table><thead><tr><th>Status</th><th>Duration</th><th>Failed stages</th><th>Record</th></tr></thead><tbody>{self._run_rows(runs)}</tbody></table></article>
<article class="panel wide"><h2>Repositories</h2><table><thead><tr><th>Repository</th><th>Status</th><th>Language</th><th>Tests</th><th>Findings</th><th>Intelligence</th></tr></thead><tbody>{repository_rows}</tbody></table></article>
</section></main></body></html>
"""
