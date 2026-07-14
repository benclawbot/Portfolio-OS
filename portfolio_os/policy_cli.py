from __future__ import annotations

import argparse
import json
from pathlib import Path

from portfolio_os.config import load_runtime_config
from portfolio_os.policy import PortfolioPolicy


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Evaluate Portfolio OS health policies")
    parser.add_argument("--runtime-config", type=Path, help="JSON runtime configuration file")
    parser.add_argument("--workspace", type=Path, help="Override the configured workspace")
    parser.add_argument("--policy", type=Path, help="Policy JSON file")
    parser.add_argument("--pretty", action="store_true", help="Print a concise human-readable summary")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    config = load_runtime_config(args.runtime_config)
    workspace = (args.workspace or config.workspace).expanduser().resolve()
    result = PortfolioPolicy(workspace, args.policy).evaluate()
    data = result.to_dict()
    if args.pretty:
        print(f"Policy: {result.status}")
        print(f"Rules evaluated: {result.evaluated_rules}")
        for item in result.violations:
            print(f"- [{item.level.upper()}] {item.message}")
        print(f"Report: {result.report_path}")
    else:
        print(json.dumps(data, indent=2))
    return 0 if result.status == "passed" else 2


if __name__ == "__main__":
    raise SystemExit(main())
