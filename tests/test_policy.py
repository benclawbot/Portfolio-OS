import json

import pytest

from portfolio_os.policy import PortfolioPolicy


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data), encoding="utf-8")


def seed(tmp_path, *, coverage=1.0, dirty=0, inaccessible=0, errors=0, regressions=0, snapshots=1, pipeline="completed"):
    write_json(
        tmp_path / "portfolio" / "portfolio-summary.json",
        {"summary": {"analysis_coverage": coverage, "dirty_count": dirty, "inaccessible_count": inaccessible, "analysis_errors": errors, "total_findings": 0}},
    )
    write_json(tmp_path / "trends" / "portfolio-trends.json", {"snapshot_count": snapshots, "regressions": [{}] * regressions})
    write_json(tmp_path / "pipeline" / "latest-run.json", {"status": pipeline})


def test_default_policy_passes_healthy_workspace(tmp_path):
    seed(tmp_path)
    result = PortfolioPolicy(tmp_path).evaluate()
    assert result.status == "passed"
    assert result.report_path.exists()


def test_fail_and_warn_levels_are_distinct(tmp_path):
    seed(tmp_path, dirty=1, errors=2)
    result = PortfolioPolicy(tmp_path).evaluate()
    assert result.status == "failed"
    assert {item.rule for item in result.violations} == {"max_dirty_count", "max_analysis_errors"}
    assert {item.level for item in result.violations} == {"warn", "fail"}


def test_custom_policy_overrides_thresholds(tmp_path):
    seed(tmp_path, coverage=0.75)
    policy = tmp_path / "policy.json"
    write_json(policy, {"rules": {"min_analysis_coverage": {"value": 0.8, "level": "fail"}}})
    result = PortfolioPolicy(tmp_path, policy).evaluate()
    assert result.status == "failed"
    assert result.violations[0].rule == "min_analysis_coverage"


def test_disabled_rule_is_not_evaluated(tmp_path):
    seed(tmp_path, errors=5)
    policy = tmp_path / "policy.json"
    write_json(policy, {"rules": {"max_analysis_errors": {"enabled": False}}})
    result = PortfolioPolicy(tmp_path, policy).evaluate()
    assert result.status == "passed"


def test_invalid_level_is_rejected(tmp_path):
    seed(tmp_path)
    policy = tmp_path / "policy.json"
    write_json(policy, {"rules": {"max_dirty_count": {"level": "maybe"}}})
    with pytest.raises(ValueError, match="invalid policy level"):
        PortfolioPolicy(tmp_path, policy).evaluate()


def test_missing_required_summary_fails_clearly(tmp_path):
    with pytest.raises(FileNotFoundError, match="portfolio-summary.json"):
        PortfolioPolicy(tmp_path).evaluate()
