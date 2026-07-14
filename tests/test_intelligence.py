from portfolio_os.intelligence import RepositoryIntelligence


def base_record(**overrides):
    record = {
        "full_name": "benclawbot/alpha",
        "default_branch": "main",
        "visibility": "private",
        "archived": False,
        "accessible": True,
        "dirty": False,
        "frameworks": ["FastAPI"],
        "file_count": 40,
        "test_file_count": 6,
        "finding_count": 0,
        "error_count": 0,
        "severity_counts": {},
    }
    record.update(overrides)
    return record


def github_evidence(**overrides):
    data = {
        "summary": {
            "combined_status": "success",
            "release_count": 1,
            "tag_count": 2,
        },
        "branches": [{"name": "main", "protected": True}],
    }
    data.update(overrides)
    return data


def test_healthy_repository_scores_high_with_explainable_factors():
    result = RepositoryIntelligence().evaluate(base_record(), {"facts": {}}, github_evidence())

    assert result["overall_score"] >= 80
    assert result["scores"]["security"]["score"] >= 85
    assert any(
        factor["key"] == "default-branch-protection"
        for factor in result["scores"]["security"]["factors"]
    )
    assert result["scores"]["release_readiness"]["confidence"] == 0.9


def test_missing_evidence_reduces_scores_and_confidence():
    result = RepositoryIntelligence().evaluate(
        base_record(frameworks=[], file_count=0, test_file_count=0),
        None,
        None,
    )

    assert result["scores"]["architecture"]["score"] < 60
    assert result["scores"]["architecture"]["confidence"] == 0.35
    assert result["scores"]["release_readiness"]["score"] < 60


def test_security_and_readiness_penalize_real_failures():
    record = base_record(
        dirty=True,
        error_count=2,
        severity_counts={"critical": 1, "high": 2},
    )
    github = github_evidence(
        summary={"combined_status": "failure", "release_count": 0, "tag_count": 0},
        branches=[{"name": "main", "protected": False}],
    )

    result = RepositoryIntelligence().evaluate(record, {"facts": {}}, github)

    assert result["scores"]["security"]["score"] <= 30
    assert result["scores"]["release_readiness"]["score"] <= 20
    assert any(
        factor["key"] == "checks-failing"
        for factor in result["scores"]["release_readiness"]["factors"]
    )


def test_archived_inaccessible_repository_is_not_release_ready():
    result = RepositoryIntelligence().evaluate(
        base_record(archived=True, accessible=False),
        {"facts": {}},
        github_evidence(),
    )

    assert result["scores"]["release_readiness"]["score"] <= 10
