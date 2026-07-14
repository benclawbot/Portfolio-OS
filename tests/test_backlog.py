import json

from portfolio_os.backlog import PortfolioBacklog


def write_summary(tmp_path, repositories):
    path = tmp_path / "portfolio" / "portfolio-summary.json"
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps({"repositories": repositories}), encoding="utf-8")


def score(value, confidence=0.9, factors=()):
    return {"score": value, "confidence": confidence, "factors": list(factors)}


def repository(**overrides):
    data = {
        "full_name": "benclawbot/alpha",
        "analysis_available": True,
        "github_index_available": True,
        "accessible": True,
        "archived": False,
        "dirty": False,
        "intelligence": {
            "scores": {
                "architecture": score(80),
                "technical_debt": score(80),
                "security": score(80),
                "release_readiness": score(80),
            }
        },
    }
    data.update(overrides)
    return data


def test_generates_ranked_evidence_backed_items(tmp_path):
    factor = {"impact": -30, "evidence": "Default branch checks are failing."}
    weak = repository(
        dirty=True,
        intelligence={
            "scores": {
                "architecture": score(55, factors=(factor,)),
                "technical_debt": score(50, factors=(factor,)),
                "security": score(40, factors=(factor,)),
                "release_readiness": score(30, factors=(factor,)),
            }
        },
    )
    write_summary(tmp_path, [weak])

    result = PortfolioBacklog(tmp_path).build()

    payload = json.loads(result.json_path.read_text())
    assert result.item_count == 5
    assert payload["items"] == sorted(payload["items"], key=lambda item: -item["priority_score"])
    assert payload["items"][0]["id"].startswith("rec-")
    assert all(item["acceptance_criteria"] for item in payload["items"])
    assert all(item["verification_plan"] for item in payload["items"])


def test_missing_evidence_creates_restoration_work(tmp_path):
    write_summary(
        tmp_path,
        [repository(analysis_available=False, github_index_available=False)],
    )

    result = PortfolioBacklog(tmp_path).build()
    payload = json.loads(result.json_path.read_text())
    categories = {item["category"] for item in payload["items"]}

    assert categories == {"analysis", "github-index"}


def test_archived_repository_only_keeps_operational_recommendations(tmp_path):
    write_summary(
        tmp_path,
        [repository(archived=True, dirty=True, analysis_available=False)],
    )

    result = PortfolioBacklog(tmp_path).build()
    payload = json.loads(result.json_path.read_text())
    categories = {item["category"] for item in payload["items"]}

    assert categories == {"analysis", "workspace"}


def test_healthy_portfolio_produces_empty_backlog(tmp_path):
    write_summary(tmp_path, [repository()])

    result = PortfolioBacklog(tmp_path).build()

    assert result.item_count == 0
    assert "No evidence-backed work" in result.markdown_path.read_text()
