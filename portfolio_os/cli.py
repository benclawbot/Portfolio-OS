from __future__ import annotations

import argparse
import json
from pathlib import Path

from portfolio_os.engine import AnalysisEngine


def load_config(path: Path) -> dict:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Portfolio OS")
    subparsers = parser.add_subparsers(dest="command", required=True)

    for command in ("inventory", "decisions", "archive-candidates"):
        command_parser = subparsers.add_parser(command)
        command_parser.add_argument("--config", default="config/portfolio.json")

    analyze = subparsers.add_parser("analyze", help="Analyze a local repository checkout")
    analyze.add_argument("path", nargs="?", default=".")
    analyze.add_argument("--output", "-o", type=Path)
    analyze.add_argument("--pretty", action="store_true", help="Print a concise human-readable summary")
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


def main() -> int:
    args = build_parser().parse_args()
    if args.command == "analyze":
        analysis = AnalysisEngine().analyze(Path(args.path))
        data = analysis.to_dict()
        if args.output:
            analysis.write_json(args.output)
        if args.pretty:
            print_summary(data)
        else:
            print(json.dumps(data, indent=2))
        return 1 if data["summary"]["error_count"] else 0

    config = load_config(Path(args.config))
    repositories = config["repositories"]
    if args.command == "inventory":
        print(json.dumps(repositories, indent=2))
    elif args.command == "archive-candidates":
        print("\n".join(repo["name"] for repo in repositories if "archive" in repo["classification"]))
    else:
        print(json.dumps({key: value for key, value in config.items() if key != "repositories"}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
