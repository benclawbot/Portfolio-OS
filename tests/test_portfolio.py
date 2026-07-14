import json

from portfolio_os.portfolio import PortfolioBuilder
from portfolio_os.sync import RepositoryState, SyncState, save_state_atomic


def repository(repo_id, name, **kwargs):
    return RepositoryState(
        id=repo_id,
        name=name,
        full_name=f"benclawbot/{name}",
        path=str(kwargs.get("path", "/missing")),
        default_branch="main",
        head_sha="abc",
        visibility="private",
        fork=False,
        archived=kwargs.get("archived", False),
        updated_at="2026-07-14T00:00:00Z",
        status=kwargs.get("status", "unchanged"),
        dirty=kwargs.get("dirty", False),
        accessible=kwargs.get("accessible", True),
    )


def test_builds_summary_and_report_from_cached_analysis(tmp_path):
    state = SyncState(
        owner="benclawbot",
        synchronized_at="2026-07-14T12:00:00Z",
        repositories={"1": repository(1, "alpha"), "2": repository(2, "beta", accessible=False)},
    )
    save_state_atomic(state, tmp_path / "sync-state.json")
    analysis_dir = tmp_path / "analysis"
    analysis_dir.mkdir()
    (analysis_dir / "1.json").write_text(
        json.dumps(
            {
                "facts": {
                    "languages": {"primary": "Python"},
                    "frameworks": {"detected": ["FastAPI"]},
                    "repository": {"file_count": 12},
                    "quality": {"test_file_count": 3},
                },
                "summary": {"finding_count": 2, "error_count": 0},
                "findings": [{"severity": "low"}, {"severity": "medium"}],
            }
        ),
        encoding="utf-8",
    )

    result = PortfolioBuilder(tmp_path).build()

    assert result.data["summary"]["repository_count"] == 2
    assert result.data["summary"]["analysis_coverage"] == 0.5
    assert result.data["languages"] == {"Python": 1}
    assert result.data["frameworks"] == {"FastAPI": 1}
    assert result.data["attention"]["inaccessible"] == ["benclawbot/beta"]
    assert result.summary_path.exists()
    assert result.report_path.exists()
    assert result.graph_path.exists()
    assert "# Portfolio Report" in result.report_path.read_text(encoding="utf-8")


def test_invalid_cached_analysis_is_reported_without_crashing(tmp_path):
    state = SyncState(owner="benclawbot", repositories={"1": repository(1, "alpha")})
    save_state_atomic(state, tmp_path / "sync-state.json")
    analysis_dir = tmp_path / "analysis"
    analysis_dir.mkdir()
    (analysis_dir / "1.json").write_text("not json", encoding="utf-8")

    result = PortfolioBuilder(tmp_path).build()

    record = result.data["repositories"][0]
    assert record["analysis_available"] is False
    assert record["analysis_error"]
    assert result.data["attention"]["missing_analysis"] == ["benclawbot/alpha"]


def test_archived_and_dirty_repositories_are_in_attention_counts(tmp_path):
    state = SyncState(
        owner="benclawbot",
        repositories={
            "1": repository(1, "archived", archived=True),
            "2": repository(2, "dirty", dirty=True, status="dirty"),
        },
    )
    save_state_atomic(state, tmp_path / "sync-state.json")

    result = PortfolioBuilder(tmp_path).build()

    assert result.data["summary"]["archived_count"] == 1
    assert result.data["summary"]["dirty_count"] == 1
    assert result.data["attention"]["dirty"] == ["benclawbot/dirty"]
    assert result.data["attention"]["archived"] == ["benclawbot/archived"]
