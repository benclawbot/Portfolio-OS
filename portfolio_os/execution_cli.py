from __future__ import annotations

import argparse
import json
from pathlib import Path

from portfolio_os.config import load_runtime_config
from portfolio_os.execution import MedusaExecutionBridge


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Accept and execute Portfolio OS recommendations with Medusa")
    parser.add_argument("--runtime-config", type=Path, help="JSON runtime configuration file")
    parser.add_argument("--workspace", type=Path, help="Override the configured workspace")
    parser.add_argument("--medusa-binary", default="medusa", help="Medusa executable path")
    subparsers = parser.add_subparsers(dest="command", required=True)
    accept = subparsers.add_parser("accept", help="Create a durable execution request")
    accept.add_argument("recommendation_id")
    execute = subparsers.add_parser("execute", help="Execute an accepted request with Medusa")
    execute.add_argument("request_id")
    subparsers.add_parser("requests", help="List accepted execution requests")
    subparsers.add_parser("receipts", help="List execution receipts")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    config = load_runtime_config(args.runtime_config)
    workspace = (args.workspace or config.workspace).expanduser().resolve()
    bridge = MedusaExecutionBridge(workspace, medusa_binary=args.medusa_binary)
    if args.command == "accept":
        payload = bridge.accept(args.recommendation_id).to_dict()
    elif args.command == "execute":
        payload = bridge.execute(args.request_id).to_dict()
    elif args.command == "requests":
        payload = {"requests": [item.to_dict() for item in bridge.list_requests()]}
    else:
        payload = {"receipts": [item.to_dict() for item in bridge.list_receipts()]}
    print(json.dumps(payload, indent=2))
    if args.command == "execute" and payload.get("status") == "failed":
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
