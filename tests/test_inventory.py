import json
from pathlib import Path


def test_inventory_has_unique_repository_names() -> None:
    data = json.loads(Path("config/portfolio.json").read_text(encoding="utf-8"))
    names = [repo["name"] for repo in data["repositories"]]
    assert len(names) == len(set(names))
    assert len(names) >= 60


def test_safety_defaults() -> None:
    data = json.loads(Path("config/portfolio.json").read_text(encoding="utf-8"))
    assert data["archive_actions"] == "recommend_only"
    assert data["pr_actions"] == "analyze_only"
    assert data["readme_updates"]["preserve_hero_banner"] is True
