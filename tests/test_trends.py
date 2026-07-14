import json

import pytest

from portfolio_os.trends import PortfolioTrends


def write_snapshot(root, name, recorded_at, summary, repositories):
    snapshots = root / "history" / "snapshots"
    snapshots.mkdir(parents=True, exist_ok=True)
    (snapshots / name).write_text(
        json.dumps(
            {
                "schema_version": 1,
                "recorded_at": recorded_at,
                "fingerprint": name.removesuffix(".json"),
                "portfolio": {"summary": summary, "repositories": repositories},
            }
        ),
        encoding="utf-8",
    )


def repository(repo_id=1, head="a", findings=0, tests=0):
    return {
        "id": repo_id,
        "full_name": f"benclawbot/repo-{repo_id}",
        "head_sha": head,
        "finding_count": findings,
        "test_file_count": tests,
    }


def test_builds_timeline_activity_and_regressions(tmp_path):
    write_snapshot(
        tmp_path,
        "001.json",
        "2026-07-14T00:00:00Z",
        {"repository_count": 1, "analysis_coverage": 1.0, "dirty_count": 0, "total_findings": 1},
        [repository(findings=1, tests=1)],
    )
    write_snapshot(
        tmp_path,
        "002.json",
        "2026-07-15T00:00:00Z",
        {"repository_count": 1, "analysis_coverage": 0.5, "dirty_count": 1, "total_findings": 3},
        [repository(head="b", findings=3, tests=2)],
    )

    result = PortfolioTrends(tmp_path).build()

    assert result.data["snapshot_count"] == 2
    assert result.data["net_change"]["analysis_coverage"] == -0.5
    assert {item["metric"] for item in result.data["regressions"]} == {
        "analysis_coverage",
        "dirty_count",
        "total_findings",
    }
    activity = result.data["repository_activity"][0]
    assert activity["head_changes"] == 1
    assert activity["finding_change"] == 2
    assert activity["test_file_change"] == 1
    assert result.json_path.exists()
    assert result.report_path.exists()


def test_limit_uses_most_recent_snapshots(tmp_path):
    for index in range(3):
        write_snapshot(
            tmp_path,
            f"00{index}.json",
            f"2026-07-{14 + index}T00:00:00Z",
            {"repository_count": index + 1},
            [repository()],
        )
    result = PortfolioTrends(tmp_path).build(limit=2)
    assert result.data["snapshot_count"] == 2
    assert result.data["period"]["start"] == "2026-07-15T00:00:00Z"


def test_retention_is_preview_only_until_applied(tmp_path):
    for index in range(4):
        write_snapshot(
            tmp_path,
            f"00{index}.json",
            f"2026-07-{14 + index}T00:00:00Z",
            {},
            [],
        )
    trends = PortfolioTrends(tmp_path)
    plan = trends.retention_plan(2)
    assert plan["remove_count"] == 2
    assert len(list((tmp_path / "history" / "snapshots").glob("*.json"))) == 4
    applied = trends.apply_retention(2)
    assert applied["applied"] is True
    assert len(list((tmp_path / "history" / "snapshots").glob("*.json"))) == 2


def test_retention_requires_at_least_one_snapshot(tmp_path):
    with pytest.raises(ValueError, match="at least 1"):
        PortfolioTrends(tmp_path).retention_plan(0)


def test_invalid_snapshots_are_skipped(tmp_path):
    snapshots = tmp_path / "history" / "snapshots"
    snapshots.mkdir(parents=True)
    (snapshots / "bad.json").write_text("not json", encoding="utf-8")
    result = PortfolioTrends(tmp_path).build()
    assert result.data["snapshot_count"] == 0
