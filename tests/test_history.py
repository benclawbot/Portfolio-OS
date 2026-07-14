import json

from portfolio_os.history import PortfolioHistory


def portfolio(repositories, **summary):
    return {
        "summary": {
            "repository_count": len(repositories),
            "active_count": len(repositories),
            "total_findings": summary.get("total_findings", 0),
        },
        "repositories": repositories,
    }


def repository(repo_id, name, **kwargs):
    return {
        "id": repo_id,
        "name": name,
        "full_name": f"benclawbot/{name}",
        "head_sha": kwargs.get("head_sha", "a"),
        "visibility": "private",
        "archived": False,
        "accessible": True,
        "dirty": False,
        "primary_language": kwargs.get("primary_language", "Python"),
        "file_count": kwargs.get("file_count", 1),
        "test_file_count": kwargs.get("test_file_count", 0),
        "finding_count": kwargs.get("finding_count", 0),
        "error_count": 0,
    }


def test_first_snapshot_is_baseline(tmp_path):
    result = PortfolioHistory(tmp_path).record(
        portfolio([repository(1, "alpha")]), recorded_at="2026-07-14T12:00:00+00:00"
    )
    assert result.delta["baseline"] is True
    assert result.delta["summary"] == {"added_count": 1, "removed_count": 0, "changed_count": 0}
    assert result.snapshot_path.exists()
    assert result.latest_path.exists()
    assert result.delta_path.exists()


def test_detects_added_removed_and_changed_repositories(tmp_path):
    history = PortfolioHistory(tmp_path)
    history.record(
        portfolio([repository(1, "alpha"), repository(2, "beta")], total_findings=1),
        recorded_at="2026-07-14T12:00:00+00:00",
    )
    result = history.record(
        portfolio(
            [repository(1, "alpha", head_sha="b", file_count=4, finding_count=2), repository(3, "gamma")],
            total_findings=2,
        ),
        recorded_at="2026-07-15T12:00:00+00:00",
    )
    assert result.delta["baseline"] is False
    assert result.delta["summary"] == {"added_count": 1, "removed_count": 1, "changed_count": 1}
    assert result.delta["added"][0]["full_name"] == "benclawbot/gamma"
    assert result.delta["removed"][0]["full_name"] == "benclawbot/beta"
    fields = result.delta["changed"][0]["fields"]
    assert fields["head_sha"] == {"before": "a", "after": "b"}
    assert fields["file_count"] == {"before": 1, "after": 4}
    assert result.delta["summary_delta"]["total_findings"]["change"] == 1


def test_snapshot_fingerprint_is_deterministic(tmp_path):
    data = portfolio([repository(1, "alpha")])
    first = PortfolioHistory(tmp_path).record(data, recorded_at="2026-07-14T12:00:00+00:00")
    second = PortfolioHistory(tmp_path).record(data, recorded_at="2026-07-15T12:00:00+00:00")
    first_data = json.loads(first.snapshot_path.read_text(encoding="utf-8"))
    second_data = json.loads(second.snapshot_path.read_text(encoding="utf-8"))
    assert first_data["fingerprint"] == second_data["fingerprint"]
    assert second.delta["summary"] == {"added_count": 0, "removed_count": 0, "changed_count": 0}
