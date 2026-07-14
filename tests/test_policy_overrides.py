import json

import pytest

from portfolio_os.policy import PortfolioPolicy


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data), encoding="utf-8")


def seed(tmp_path):
    write_json(
        tmp_path / "portfolio" / "portfolio-summary.json",
        {
            "summary": {"analysis_coverage": 1.0, "dirty_count": 0, "inaccessible_count": 0, "analysis_errors": 0, "total_findings": 1},
            "repositories": [
                {
                    "full_name": "benclawbot/alpha",
                    "analysis_available": True,
                    "finding_count": 1,
                    "error_count": 0,
                    "test_file_count": 2,
                    "dirty": False,
                    "accessible": True,
                }
            ],
        },
    )
    write_json(tmp_path / "trends" / "portfolio-trends.json", {"snapshot_count": 1, "regressions": []})


def test_repository_specific_rules_pass(tmp_path):
    seed(tmp_path)
    policy = tmp_path / "policy.json"
    write_json(
        policy,
        {
            "repositories": {
                "benclawbot/alpha": {
                    "require_analysis": {"value": True, "level": "fail"},
                    "min_test_files": {"value": 2, "level": "fail"},
                    "max_findings": {"value": 1, "level": "warn"},
                }
            }
        },
    )
    assert PortfolioPolicy(tmp_path, policy).evaluate().status == "passed"


def test_repository_rule_violation_identifies_repository(tmp_path):
    seed(tmp_path)
    policy = tmp_path / "policy.json"
    write_json(policy, {"repositories": {"benclawbot/alpha": {"min_test_files": {"value": 3, "level": "fail"}}}})
    result = PortfolioPolicy(tmp_path, policy).evaluate()
    assert result.status == "failed"
    assert result.violations[0].repository == "benclawbot/alpha"


def test_unknown_rule_is_rejected(tmp_path):
    seed(tmp_path)
    policy = tmp_path / "policy.json"
    write_json(policy, {"rules": {"imaginary_rule": {"value": 1, "level": "fail"}}})
    with pytest.raises(ValueError, match="unknown portfolio rules"):
        PortfolioPolicy(tmp_path, policy).evaluate()


def test_wrong_threshold_type_is_rejected(tmp_path):
    seed(tmp_path)
    policy = tmp_path / "policy.json"
    write_json(policy, {"rules": {"min_analysis_coverage": {"value": "high", "level": "fail"}}})
    with pytest.raises(ValueError, match="numeric policy value"):
        PortfolioPolicy(tmp_path, policy).evaluate()
