from __future__ import annotations

import argparse
import json
from pathlib import Path

from portfolio_os.config import load_runtime_config
from portfolio_os.github_index import GitHubMetadataIndexer
from portfolio_os.sync import GitHubAPIClient, load_state


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build the incremental GitHub metadata index")
    parser.add_argument("--runtime-config", type=Path, help="JSON runtime configuration file")
    parser.add_argument("--workspace", type=Path, help="Override the configured workspace")
    parser.add_argument("--force", action="store_true", help="Refresh all accessible repositories")
    parser.add_argument("--pretty", action="store_true", help="Print a concise human-readable summary")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    config = load_runtime_config(args.runtime_config)
    workspace = (args.workspace or config.workspace).expanduser().resolve()
    state = load_state(workspace / "sync-state.json")
    github = GitHubAPIClient(api_url=config.github.api_url)
    result = GitHubMetadataIndexer(workspace, github).build(state, force=args.force)
    data = result.to_dict()
    if args.pretty:
        print(f"Repositories: {data['repository_count']}")
        print(f"Refreshed: {data['refreshed_count']} | Reused: {data['reused_count']} | Failed: {data['failed_count']}")
        print(f"Index: {data['index_path']}")
    else:
        print(json.dumps(data, indent=2))
    return 2 if result.failed_count else 0


if __name__ == "__main__":
    raise SystemExit(main())
