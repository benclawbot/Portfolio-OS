import json

import pytest

from portfolio_os.dashboard import PortfolioDashboard


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data), encoding="utf-8")


def portfolio():
    return {
        "owner": "benclawbot",
        "summary": {
            "repository_count": 1,
            "active_count": 1,
            "analysis_coverage": 1.0,
            "total_findings": 2,
            "dirty_count": 0,
            "inaccessible_count": 0,
        },
        "languages": {"Python": 1},
        "attention": {"dirty": [], "missing_analysis": []},
        "repositories": [
            {
                "full_name": "benclawbot/<alpha>",
                "sync_status": "unchanged",
                "primary_language": "Python",
                "test_file_count": 3,
                "finding_count": 2,
            }
        ],
    }


def trends():
    return {
        "snapshot_count": 2,
        "timeline": [
            {"recorded_at": "2026-07-14", "metrics": {"analysis_coverage": 0.5}},
            {"recorded_at": "2026-07-15", "metrics": {"analysis_coverage": 1.0}},
        ],
        "regressions": [{"metric": "dirty_count", "before": 0, "after": 1}],
    }


def test_generates_self_contained_dashboard(tmp_path):
    write_json(tmp_path / "portfolio" / "portfolio-summary.json", portfolio())
    write_json(tmp_path / "trends" / "portfolio-trends.json", trends())

    result = PortfolioDashboard(tmp_path).build()

    rendered = result.html_path.read_text(encoding="utf-8")
    assert "<!doctype html>" in rendered
    assert "Portfolio OS" in rendered
    assert "analysis_coverage" in rendered
    assert "benclawbot/&lt;alpha&gt;" in rendered
    assert "<script" not in rendered
    assert "https://" not in rendered
    assert result.data_path.exists()


def test_dashboard_works_without_trend_artifact(tmp_path):
    write_json(tmp_path / "portfolio" / "portfolio-summary.json", portfolio())

    result = PortfolioDashboard(tmp_path).build()

    rendered = result.html_path.read_text(encoding="utf-8")
    data = json.loads(result.data_path.read_text(encoding="utf-8"))
    assert "No historical snapshots available." in rendered
    assert data["trends"]["snapshot_count"] == 0


def test_missing_portfolio_summary_fails_clearly(tmp_path):
    with pytest.raises(FileNotFoundError, match="portfolio-summary.json"):
        PortfolioDashboard(tmp_path).build()


def test_invalid_artifact_shape_is_rejected(tmp_path):
    write_json(tmp_path / "portfolio" / "portfolio-summary.json", [])
    with pytest.raises(ValueError, match="JSON object"):
        PortfolioDashboard(tmp_path).build()


def test_custom_output_directory_is_used(tmp_path):
    write_json(tmp_path / "portfolio" / "portfolio-summary.json", portfolio())
    output = tmp_path / "public"
    result = PortfolioDashboard(tmp_path, output).build()
    assert result.html_path == output / "index.html"
    assert result.data_path == output / "dashboard-data.json"
