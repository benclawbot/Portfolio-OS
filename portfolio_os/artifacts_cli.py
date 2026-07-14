from __future__ import annotations

import argparse
import json
from pathlib import Path

from portfolio_os.artifacts import ArtifactManager
from portfolio_os.config import load_runtime_config


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Manage Portfolio OS generated artifacts")
    parser.add_argument("--runtime-config", type=Path, help="JSON runtime configuration file")
    parser.add_argument("--workspace", type=Path, help="Override the configured workspace")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("catalog", help="Rebuild the artifact catalog")
    resolve = subparsers.add_parser("resolve", help="Resolve an artifact ID")
    resolve.add_argument("artifact_id")
    plan = subparsers.add_parser("retention-plan", help="Plan non-destructive artifact retention")
    plan.add_argument("--keep-history", type=int, default=30)
    plan.add_argument("--keep-runs", type=int, default=100)
    apply = subparsers.add_parser("apply-retention", help="Apply an explicitly generated retention plan")
    apply.add_argument("plan", type=Path)
    apply.add_argument("--confirm", action="store_true", help="Required destructive confirmation")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    config = load_runtime_config(args.runtime_config)
    workspace = (args.workspace or config.workspace).expanduser().resolve()
    manager = ArtifactManager(workspace)
    if args.command == "catalog":
        payload = manager.build_catalog().to_dict()
    elif args.command == "resolve":
        payload = {"path": str(manager.resolve(args.artifact_id))}
    elif args.command == "retention-plan":
        payload = manager.retention_plan(keep_history=args.keep_history, keep_runs=args.keep_runs)
    else:
        plan = json.loads(args.plan.read_text(encoding="utf-8"))
        payload = manager.apply_retention(plan, confirm=args.confirm)
    print(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
