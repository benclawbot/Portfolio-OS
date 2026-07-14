from __future__ import annotations

import argparse
import json
from pathlib import Path

from portfolio_os.backlog import PortfolioBacklog
from portfolio_os.config import load_runtime_config


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate the evidence-backed portfolio backlog")
    parser.add_argument("--runtime-config", type=Path, help="JSON runtime configuration file")
    parser.add_argument("--workspace", type=Path, help="Override the configured workspace")
    parser.add_argument("--pretty", action="store_true", help="Print a concise human-readable summary")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    config = load_runtime_config(args.runtime_config)
    workspace = (args.workspace or config.workspace).expanduser().resolve()
    result = PortfolioBacklog(workspace).build()
    data = result.to_dict()
    if args.pretty:
        print(f"Backlog items: {data['item_count']}")
        print(f"JSON: {data['json_path']}")
        print(f"Markdown: {data['markdown_path']}")
    else:
        print(json.dumps(data, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
