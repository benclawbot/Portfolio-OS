from __future__ import annotations

import argparse
import json
from pathlib import Path

from portfolio_os.config import load_runtime_config
from portfolio_os.service import PortfolioService, serve


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the Portfolio OS local service or worker")
    parser.add_argument("--runtime-config", type=Path, help="JSON runtime configuration file")
    parser.add_argument("--workspace", type=Path, help="Override the configured workspace")
    subparsers = parser.add_subparsers(dest="command", required=True)
    server = subparsers.add_parser("serve", help="Run the local REST API")
    server.add_argument("--host", default="127.0.0.1")
    server.add_argument("--port", type=int, default=8765)
    subparsers.add_parser("run-next", help="Execute the oldest pending job")
    jobs = subparsers.add_parser("jobs", help="List durable jobs")
    jobs.add_argument("--status", choices=("pending", "running", "completed", "failed"))
    return parser


def main() -> int:
    args = build_parser().parse_args()
    config = load_runtime_config(args.runtime_config)
    workspace = (args.workspace or config.workspace).expanduser().resolve()
    if args.command == "serve":
        serve(workspace, args.host, args.port)
        return 0
    service = PortfolioService(workspace)
    if args.command == "run-next":
        result = service.run_next()
        print(json.dumps({"job": result}, indent=2))
        return 2 if result and result["status"] == "failed" else 0
    print(json.dumps({"jobs": [item.to_dict() for item in service.jobs.list(args.status)]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
