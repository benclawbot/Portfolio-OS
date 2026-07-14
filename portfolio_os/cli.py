from __future__ import annotations

import argparse
import difflib
import json
import sys
from pathlib import Path

from portfolio_os.config import PortfolioConfig, load_runtime_config
from portfolio_os.dna import DNABuilder, SimilarityEngine
from portfolio_os.engine import AnalysisEngine
from portfolio_os.graph import GraphBuilder, GraphQuery, GraphStore, KnowledgeGraph
from portfolio_os.logging import configure_logging
from portfolio_os.plugins import PluginRegistry
from portfolio_os.readme import ReadmeGenerator
from portfolio_os.sync import GitHubAPIClient, SubprocessGitClient, WorkspaceSynchronizer, load_state


def load_inventory_config(path: Path) -> dict:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Portfolio OS")
    parser.add_argument("--runtime-config", type=Path, help="JSON runtime configuration file")
    parser.add_argument("--log-level", help="Override configured log level")
    parser.add_argument("--json-logs", action="store_true", help="Emit structured JSON logs")
    subparsers = parser.add_subparsers(dest="command", required=True)
    for command in ("inventory", "decisions", "archive-candidates"):
        command_parser = subparsers.add_parser(command)
        command_parser.add_argument("--config", default="config/portfolio.json")

    sync = subparsers.add_parser("sync", help="Synchronize the managed GitHub workspace")
    sync.add_argument("--workspace", type=Path, help="Override the configured workspace")
    sync.add_argument("--owner", help="Override the configured GitHub owner")
    sync.add_argument("--no-analyze", action="store_true", help="Skip changed-repository analysis")
    sync.add_argument("--pretty", action="store_true", help="Print a concise human-readable summary")

    status = subparsers.add_parser("workspace-status", help="Read the persisted synchronization state")
    status.add_argument("--workspace", type=Path, help="Override the configured workspace")
    status.add_argument("--pretty", action="store_true", help="Print a concise human-readable summary")

    analyze = subparsers.add_parser("analyze")
    analyze.add_argument("path", nargs="?", default=".")
    analyze.add_argument("--output", "-o", type=Path)
    analyze.add_argument("--pretty", action="store_true")
    analyze.add_argument("--discover-plugins", action="store_true")

    subparsers.add_parser("plugins", help="List registered analyzer plugins")

    readme = subparsers.add_parser("readme")
    readme.add_argument("path", nargs="?", default=".")
    readme.add_argument("--output", "-o", type=Path)
    readme.add_argument("--write", action="store_true")
    readme.add_argument("--check", action="store_true")
    readme.add_argument("--diff", action="store_true")
    readme.add_argument("--no-preserve-hero", action="store_true")

    dna = subparsers.add_parser("dna")
    dna.add_argument("path", nargs="?", default=".")
    dna.add_argument("--output", "-o", type=Path)

    compare = subparsers.add_parser("compare")
    compare.add_argument("left")
    compare.add_argument("right")
    compare.add_argument("--output", "-o", type=Path)
    compare.add_argument("--pretty", action="store_true")

    graph_build = subparsers.add_parser("graph-build", help="Build a graph from local repository checkouts")
    graph_build.add_argument("paths", nargs="+")
    graph_build.add_argument("--output", "-o", type=Path, default=Path("reports/latest/portfolio-graph.json"))
    graph_build.add_argument("--threshold", type=float, default=0.55)

    graph_query = subparsers.add_parser("graph-query", help="Query a saved portfolio graph")
    graph_query.add_argument("graph", type=Path)
    graph_query.add_argument("node")
    graph_query.add_argument("--incoming", action="store_true")
    graph_query.add_argument("--relation")
    graph_query.add_argument("--impact", action="store_true")
    graph_query.add_argument("--max-depth", type=int, default=5)

    graph_path = subparsers.add_parser("graph-path", help="Find a relationship path")
    graph_path.add_argument("graph", type=Path)
    graph_path.add_argument("source")
    graph_path.add_argument("target")
    return parser


def print_summary(data: dict) -> None:
    summary = data["summary"]
    facts = data["facts"]
    print(f"Repository: {data['repository']}")
    print(f"Primary language: {facts.get('languages', {}).get('primary') or 'unknown'}")
    print(f"Files: {facts.get('repository', {}).get('file_count', 0)}")
    print(f"Tests: {facts.get('quality', {}).get('test_file_count', 0)}")
    print(f"Findings: {summary['finding_count']} | Errors: {summary['error_count']}")
    for finding in data["findings"]:
        print(f"- [{finding['severity'].upper()}] {finding['title']}")


def print_sync_summary(data: dict) -> None:
    summary = data["summary"]
    print(f"Repositories: {summary['repository_count']}")
    print(f"Analyzed: {summary['analyzed_count']} | Dirty: {summary['dirty_count']}")
    for status, count in sorted(summary["status_counts"].items()):
        print(f"- {status}: {count}")


def make_engine(config: PortfolioConfig, *, discover_plugins: bool = False) -> AnalysisEngine:
    return AnalysisEngine(config=config, discover_plugins=discover_plugins)


def handle_sync(args: argparse.Namespace, config: PortfolioConfig) -> int:
    workspace = (args.workspace or config.workspace).expanduser()
    owner = args.owner or config.github.owner
    synchronizer = WorkspaceSynchronizer(
        workspace=workspace,
        owner=owner,
        github=GitHubAPIClient(api_url=config.github.api_url),
        git=SubprocessGitClient(),
        analyzer=None if args.no_analyze else make_engine(config),
    )
    data = synchronizer.synchronize(analyze_changed=not args.no_analyze).to_dict()
    print_sync_summary(data) if args.pretty else print(json.dumps(data, indent=2))
    unsafe = {"dirty", "path-conflict", "remote-mismatch"}
    return 2 if any(item["status"] in unsafe for item in data["repositories"]) else 0


def handle_workspace_status(args: argparse.Namespace, config: PortfolioConfig) -> int:
    workspace = (args.workspace or config.workspace).expanduser().resolve()
    state = load_state(workspace / "sync-state.json")
    repositories = tuple(state.repositories[key] for key in sorted(state.repositories))
    counts: dict[str, int] = {}
    for repository in repositories:
        counts[repository.status] = counts.get(repository.status, 0) + 1
    data = {
        "state_path": str(workspace / "sync-state.json"),
        "summary": {
            "repository_count": len(repositories),
            "analyzed_count": sum(item.analyzed for item in repositories),
            "dirty_count": sum(item.dirty for item in repositories),
            "status_counts": counts,
        },
        "repositories": [item.__dict__ for item in repositories],
    }
    print_sync_summary(data) if args.pretty else print(json.dumps(data, indent=2))
    return 0


def handle_readme(args: argparse.Namespace, config: PortfolioConfig) -> int:
    root = Path(args.path).expanduser().resolve()
    analysis = make_engine(config).analyze(root)
    generator = ReadmeGenerator(preserve_hero=not args.no_preserve_hero)
    generated = generator.generate(root, analysis)
    current_path = root / "README.md"
    current = current_path.read_text(encoding="utf-8", errors="replace") if current_path.exists() else ""
    if args.diff:
        sys.stdout.writelines(
            difflib.unified_diff(
                current.splitlines(keepends=True),
                generated.splitlines(keepends=True),
                fromfile=str(current_path),
                tofile=f"{current_path} (generated)",
            )
        )
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(generated, encoding="utf-8", newline="\n")
    if args.write:
        generator.write(root, generated)
    if not any((args.diff, args.output, args.write, args.check)):
        print(generated, end="")
    return 2 if args.check and current != generated else 0


def handle_dna(args: argparse.Namespace, config: PortfolioConfig) -> int:
    data = DNABuilder().build(make_engine(config).analyze(Path(args.path))).to_dict()
    text = json.dumps(data, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding="utf-8")
    else:
        print(text, end="")
    return 0


def handle_compare(args: argparse.Namespace, config: PortfolioConfig) -> int:
    engine = make_engine(config)
    builder = DNABuilder()
    result = SimilarityEngine().compare(
        builder.build(engine.analyze(Path(args.left))), builder.build(engine.analyze(Path(args.right)))
    )
    text = json.dumps(result.to_dict(), indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding="utf-8")
    if args.pretty:
        print(f"{result.left} vs {result.right}: {result.score:.1%} ({result.classification})")
        for reason in result.reasons:
            print(f"- {reason}")
    elif not args.output:
        print(text, end="")
    return 0


def handle_graph_build(args: argparse.Namespace) -> int:
    graph = KnowledgeGraph()
    builder = GraphBuilder()
    for path in args.paths:
        builder.add_repository(graph, Path(path))
    builder.infer_repository_relationships(graph, args.threshold)
    GraphStore().save(graph, args.output)
    print(json.dumps(graph.to_dict()["summary"], indent=2))
    return 0


def main() -> int:
    args = build_parser().parse_args()
    runtime_config = load_runtime_config(args.runtime_config)
    configure_logging(args.log_level or runtime_config.logging.level, args.json_logs or runtime_config.logging.json)

    if args.command == "sync":
        return handle_sync(args, runtime_config)
    if args.command == "workspace-status":
        return handle_workspace_status(args, runtime_config)
    if args.command == "plugins":
        registry = PluginRegistry()
        print(json.dumps([{"name": item.name, "source": item.source} for item in registry.descriptors()], indent=2))
        return 0
    if args.command == "analyze":
        analysis = make_engine(runtime_config, discover_plugins=args.discover_plugins).analyze(Path(args.path))
        data = analysis.to_dict()
        if args.output:
            analysis.write_json(args.output)
        print_summary(data) if args.pretty else print(json.dumps(data, indent=2))
        return 1 if data["summary"]["error_count"] else 0
    if args.command == "readme":
        return handle_readme(args, runtime_config)
    if args.command == "dna":
        return handle_dna(args, runtime_config)
    if args.command == "compare":
        return handle_compare(args, runtime_config)
    if args.command == "graph-build":
        return handle_graph_build(args)
    if args.command in {"graph-query", "graph-path"}:
        graph = GraphStore().load(args.graph)
        query = GraphQuery(graph)
        if args.command == "graph-path":
            print(json.dumps(query.path(args.source, args.target), indent=2))
        elif args.impact:
            print(json.dumps(query.impact(args.node, args.max_depth), indent=2))
        else:
            print(json.dumps([edge.__dict__ for edge in query.neighbors(args.node, args.relation, args.incoming)], indent=2))
        return 0

    inventory_config = load_inventory_config(Path(args.config))
    repositories = inventory_config["repositories"]
    if args.command == "inventory":
        print(json.dumps(repositories, indent=2))
    elif args.command == "archive-candidates":
        print("\n".join(repo["name"] for repo in repositories if "archive" in repo["classification"]))
    else:
        print(json.dumps({key: value for key, value in inventory_config.items() if key != "repositories"}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
