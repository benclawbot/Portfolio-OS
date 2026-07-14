from __future__ import annotations

import argparse
import json
from pathlib import Path

from portfolio_os.config import load_runtime_config
from portfolio_os.workspace import WorkspaceValidator


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate Portfolio OS workspace artifacts")
    parser.add_argument("command", choices=("validate", "repair-plan"))
    parser.add_argument("--runtime-config", type=Path)
    parser.add_argument("--workspace", type=Path)
    parser.add_argument("--pretty", action="store_true")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    config = load_runtime_config(args.runtime_config)
    workspace = (args.workspace or config.workspace).expanduser().resolve()
    validator = WorkspaceValidator(workspace)
    if args.command == "repair-plan":
        data = validator.repair_plan()
    else:
        result = validator.validate()
        data = result.to_dict()
    if args.pretty:
        print(f"Workspace: {data['status']}")
        if args.command == "repair-plan":
            print(f"Stages: {', '.join(data['stages']) or 'none'}")
        else:
            summary = data["summary"]
            print(f"Passed: {summary['passed']} Warnings: {summary['warnings']} Failed: {summary['failed']}")
            print(f"Manifest: {data['manifest_path']}")
    else:
        print(json.dumps(data, indent=2))
    return 0 if data["status"] == "passed" else 2


if __name__ == "__main__":
    raise SystemExit(main())
