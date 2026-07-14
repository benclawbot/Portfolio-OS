from __future__ import annotations

import argparse
import json
from pathlib import Path

from portfolio_os.config import load_runtime_config
from portfolio_os.operations import RefreshOperations


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Inspect Portfolio OS refresh operations")
    parser.add_argument("command", choices=("runs", "lock-status", "clear-stale-lock"))
    parser.add_argument("--runtime-config", type=Path)
    parser.add_argument("--workspace", type=Path)
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument("--stale-after", type=float, default=3600)
    parser.add_argument("--pretty", action="store_true")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    config = load_runtime_config(args.runtime_config)
    workspace = (args.workspace or config.workspace).expanduser().resolve()
    operations = RefreshOperations(workspace)
    if args.command == "runs":
        data = {"runs": operations.list_runs(args.limit)}
    elif args.command == "lock-status":
        data = operations.inspect_lock(args.stale_after).to_dict()
    else:
        data = operations.clear_stale_lock(args.stale_after).to_dict()
        data["cleared"] = True
    if args.pretty:
        if args.command == "runs":
            print(f"Runs: {len(data['runs'])}")
            for run in data["runs"]:
                print(f"- {run.get('status', 'unknown')} {run.get('duration_seconds', 0):.3f}s {run['path']}")
        else:
            print(json.dumps(data, indent=2))
    else:
        print(json.dumps(data, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
