from __future__ import annotations

import argparse
import json
from pathlib import Path

from portfolio_os.config import load_runtime_config
from portfolio_os.dashboard import PortfolioDashboard


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate a static Portfolio OS dashboard")
    parser.add_argument("--runtime-config", type=Path, help="JSON runtime configuration file")
    parser.add_argument("--workspace", type=Path, help="Override the configured workspace")
    parser.add_argument("--output-dir", type=Path, help="Override the dashboard output directory")
    parser.add_argument("--pretty", action="store_true", help="Print a concise human-readable summary")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    config = load_runtime_config(args.runtime_config)
    workspace = (args.workspace or config.workspace).expanduser().resolve()
    result = PortfolioDashboard(workspace, args.output_dir).build()
    if args.pretty:
        print(f"Dashboard: {result.html_path}")
        print(f"Data: {result.data_path}")
    else:
        print(json.dumps({"html_path": str(result.html_path), "data_path": str(result.data_path)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
