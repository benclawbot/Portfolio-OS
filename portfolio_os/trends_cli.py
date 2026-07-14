from __future__ import annotations

import argparse
import json
from pathlib import Path

from portfolio_os.config import load_runtime_config
from portfolio_os.trends import PortfolioTrends


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Analyze portfolio history trends")
    parser.add_argument("--runtime-config", type=Path, help="JSON runtime configuration file")
    parser.add_argument("--workspace", type=Path, help="Override the configured workspace")
    parser.add_argument("--output-dir", type=Path, help="Override the trend artifact directory")
    parser.add_argument("--limit", type=int, help="Use only the most recent N snapshots")
    parser.add_argument("--retain", type=int, help="Preview retention of the newest N snapshots")
    parser.add_argument("--apply-retention", action="store_true", help="Apply the retention plan")
    parser.add_argument("--pretty", action="store_true", help="Print a concise human-readable summary")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    config = load_runtime_config(args.runtime_config)
    workspace = (args.workspace or config.workspace).expanduser().resolve()
    trends = PortfolioTrends(workspace, args.output_dir)
    retention = None
    if args.retain is not None:
        retention = (
            trends.apply_retention(args.retain)
            if args.apply_retention
            else trends.retention_plan(args.retain)
        )
    result = trends.build(args.limit)
    if args.pretty:
        print(f"Snapshots: {result.data['snapshot_count']}")
        print(f"Regressions: {len(result.data['regressions'])}")
        print(f"Trend JSON: {result.json_path}")
        print(f"Trend report: {result.report_path}")
        if retention:
            action = "Removed" if retention.get("applied") else "Would remove"
            print(f"{action}: {retention['remove_count']} snapshots")
    else:
        payload = {
            "json_path": str(result.json_path),
            "report_path": str(result.report_path),
            "summary": {
                "snapshot_count": result.data["snapshot_count"],
                "regression_count": len(result.data["regressions"]),
                "period": result.data["period"],
            },
        }
        if retention:
            payload["retention"] = retention
        print(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
