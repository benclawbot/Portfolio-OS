from __future__ import annotations

import argparse
import json
from pathlib import Path


def load_config(path: Path) -> dict:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def main() -> int:
    parser = argparse.ArgumentParser(description="Portfolio OS")
    parser.add_argument("command", choices=["inventory", "decisions", "archive-candidates"])
    parser.add_argument("--config", default="config/portfolio.json")
    args = parser.parse_args()
    config = load_config(Path(args.config))
    repos = config["repositories"]
    if args.command == "inventory":
        print(json.dumps(repos, indent=2))
    elif args.command == "archive-candidates":
        print("\n".join(r["name"] for r in repos if "archive" in r["classification"]))
    else:
        print(json.dumps({k: v for k, v in config.items() if k != "repositories"}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
