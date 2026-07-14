import json

from portfolio_os.reuse import PortfolioReuseAnalyzer
from portfolio_os.sync import RepositoryState, SyncState, save_state_atomic


def state(repo_id, name, path):
    return RepositoryState(
        id=repo_id,
        name=name,
        full_name=f"benclawbot/{name}",
        path=str(path),
        default_branch="main",
        head_sha="abc",
        visibility="private",
        fork=False,
        archived=False,
        updated_at="2026-07-14T00:00:00Z",
        status="unchanged",
    )


def test_detects_exact_cross_repository_source_duplication(tmp_path):
    left = tmp_path / "repositories" / "left"
    right = tmp_path / "repositories" / "right"
    left.mkdir(parents=True)
    right.mkdir(parents=True)
    content = "def shared(value):\n    result = value * 2\n    return result\n\nprint(shared(3))\n"
    (left / "utils.py").write_text(content, encoding="utf-8")
    (right / "helpers.py").write_text(content.replace("\n", "\r\n"), encoding="utf-8")
    sync = SyncState(
        owner="benclawbot",
        repositories={"1": state(1, "left", left), "2": state(2, "right", right)},
    )
    save_state_atomic(sync, tmp_path / "sync-state.json")

    result = PortfolioReuseAnalyzer(tmp_path, minimum_bytes=20, minimum_lines=3).build()

    payload = json.loads(result.json_path.read_text())
    assert result.duplicate_group_count == 1
    assert len(payload["groups"][0]["occurrences"]) == 2
    assert "shared library" in payload["groups"][0]["recommendation"]


def test_ignores_duplicates_within_one_repository(tmp_path):
    root = tmp_path / "repositories" / "alpha"
    root.mkdir(parents=True)
    content = "def repeated():\n    value = 1\n    return value\n"
    (root / "a.py").write_text(content, encoding="utf-8")
    (root / "b.py").write_text(content, encoding="utf-8")
    save_state_atomic(
        SyncState(owner="benclawbot", repositories={"1": state(1, "alpha", root)}),
        tmp_path / "sync-state.json",
    )

    result = PortfolioReuseAnalyzer(tmp_path, minimum_bytes=10, minimum_lines=2).build()

    assert result.duplicate_group_count == 0
