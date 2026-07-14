from __future__ import annotations

import argparse
import difflib
import json
import sys
from pathlib import Path

from portfolio_os.engine import AnalysisEngine
from portfolio_os.readme import ReadmeGenerator


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

    readme = subparsers.add_parser("readme", help="Generate an evidence-based README for a local checkout")
    readme.add_argument("path", nargs="?", default=".")
    readme.add_argument("--output", "-o", type=Path, help="Write a candidate README to another path")
    readme.add_argument("--write", action="store_true", help="Atomically replace README.md")
    readme.add_argument("--check", action="store_true", help="Exit 2 when README.md differs from generated output")
    readme.add_argument("--diff", action="store_true", help="Print a unified diff against README.md")
    readme.add_argument("--no-preserve-hero", action="store_true", help="Do not preserve the existing leading hero banner")
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


def handle_readme(args: argparse.Namespace) -> int:
    root = Path(args.path).expanduser().resolve()
    analysis = AnalysisEngine().analyze(root)
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
    if args.check and current != generated:
        return 2
    return 0


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
    if args.command == "readme":
        return handle_readme(args)

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
