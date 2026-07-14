from __future__ import annotations

import argparse
import json
from pathlib import Path

from portfolio_os.config import load_runtime_config
from portfolio_os.engine import AnalysisEngine
from portfolio_os.github_index import GitHubMetadataIndexer
from portfolio_os.pipeline import PipelineLockedError, PortfolioPipeline
from portfolio_os.sync import GitHubAPIClient, SubprocessGitClient, WorkspaceSynchronizer, load_state


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the complete Portfolio OS refresh pipeline")
    parser.add_argument("--runtime-config", type=Path, help="JSON runtime configuration file")
    parser.add_argument("--workspace", type=Path, help="Override the configured workspace")
    parser.add_argument("--owner", help="Override the configured GitHub owner")
    parser.add_argument("--skip-sync", action="store_true", help="Build artifacts from existing workspace state")
    parser.add_argument("--skip-github-index", action="store_true", help="Skip GitHub metadata indexing")
    parser.add_argument("--force-github-index", action="store_true", help="Refresh all GitHub metadata artifacts")
    parser.add_argument("--no-analyze", action="store_true", help="Skip changed-repository analysis during sync")
    parser.add_argument("--continue-on-error", action="store_true", help="Attempt later stages after a stage failure")
    parser.add_argument("--threshold", type=float, default=0.55, help="Repository similarity threshold")
    parser.add_argument("--trend-limit", type=int, help="Use only the latest N snapshots for trends")
    parser.add_argument("--policy", type=Path, help="Policy JSON file to enforce as the final stage")
    parser.add_argument("--enforce-policy", action="store_true", help="Run the built-in or supplied policy as the final stage")
    parser.add_argument("--pretty", action="store_true", help="Print a concise human-readable summary")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    config = load_runtime_config(args.runtime_config)
    workspace = (args.workspace or config.workspace).expanduser().resolve()
    owner = args.owner or config.github.owner

    sync_stage = None
    if not args.skip_sync:
        github = GitHubAPIClient(api_url=config.github.api_url)
        synchronizer = WorkspaceSynchronizer(
            workspace=workspace,
            owner=owner,
            github=github,
            git=SubprocessGitClient(),
            analyzer=None if args.no_analyze else AnalysisEngine(config=config),
        )

        def run_sync() -> dict:
            sync_result = synchronizer.synchronize(analyze_changed=not args.no_analyze).to_dict()
            if args.skip_github_index:
                sync_result["github_index"] = {"status": "skipped"}
            else:
                state = load_state(workspace / "sync-state.json")
                index_result = GitHubMetadataIndexer(workspace, github).build(
                    state,
                    force=args.force_github_index,
                )
                sync_result["github_index"] = index_result.to_dict()
                if index_result.failed_count:
                    raise RuntimeError(
                        f"GitHub metadata indexing failed for {index_result.failed_count} repositories"
                    )
            return sync_result

        sync_stage = run_sync

    pipeline = PortfolioPipeline(
        workspace,
        sync_stage=sync_stage,
        similarity_threshold=args.threshold,
        trend_limit=args.trend_limit,
        policy_path=args.policy,
        enforce_policy=args.enforce_policy or args.policy is not None,
    )
    try:
        result = pipeline.run(continue_on_error=args.continue_on_error)
    except PipelineLockedError as error:
        print(str(error))
        return 3

    data = result.to_dict()
    if args.pretty:
        print(f"Pipeline: {data['status']}")
        for stage in data["stages"]:
            suffix = f" — {stage['error']}" if stage.get("error") else ""
            print(f"- {stage['name']}: {stage['status']} ({stage['duration_seconds']:.3f}s){suffix}")
        print(f"Run report: {pipeline.result_path}")
    else:
        print(json.dumps(data, indent=2))
    return 0 if result.status == "completed" else 2


if __name__ == "__main__":
    raise SystemExit(main())
