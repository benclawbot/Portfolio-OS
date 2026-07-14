from __future__ import annotations

import argparse
import json
from pathlib import Path

from portfolio_os.config import load_runtime_config
from portfolio_os.portfolio import PortfolioBuilder


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build portfolio-wide artifacts from a managed workspace")
    parser.add_argument("--runtime-config", type=Path, help="JSON runtime configuration file")
    parser.add_argument("--workspace", type=Path, help="Override the configured workspace")
    parser.add_argument("--output-dir", type=Path, help="Override the artifact output directory")
    parser.add_argument("--threshold", type=float, default=0.55, help="Repository similarity threshold")
    parser.add_argument("--pretty", action="store_true", help="Print a concise human-readable summary")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    config = load_runtime_config(args.runtime_config)
    workspace = args.workspace or config.workspace
    result = PortfolioBuilder(workspace, args.output_dir).build(args.threshold)
    if args.pretty:
        summary = result.data["summary"]
        print(f"Repositories: {summary['repository_count']}")
        print(f"Active: {summary['active_count']} | Archived: {summary['archived_count']}")
        print(f"Analysis coverage: {summary['analysis_coverage']:.1%}")
        print(f"Findings: {summary['total_findings']} | Analysis errors: {summary['analysis_errors']}")
        print(f"Summary: {result.summary_path}")
        print(f"Report: {result.report_path}")
        print(f"Graph: {result.graph_path}")
    else:
        print(
            json.dumps(
                {
                    "summary_path": str(result.summary_path),
                    "report_path": str(result.report_path),
                    "graph_path": str(result.graph_path),
                    "summary": result.data["summary"],
                },
                indent=2,
            )
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
