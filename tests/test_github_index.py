import json

from portfolio_os.github_index import GitHubMetadataIndexer
from portfolio_os.sync import RepositoryState, SyncState


class FakeGitHub:
    def __init__(self):
        self.calls = []
        self.fail_path = None

    def _request(self, path):
        self.calls.append(path)
        if self.fail_path and self.fail_path in path:
            raise RuntimeError("boom")
        if "/branches?" in path:
            return [{"name": "main", "commit": {"sha": "abc"}, "protected": True}]
        if "/tags?" in path:
            return [{"name": "v1.0.0", "commit": {"sha": "tagsha"}}]
        if "/releases?" in path:
            return [
                {
                    "id": 10,
                    "tag_name": "v1.0.0",
                    "name": "Stable",
                    "draft": False,
                    "prerelease": False,
                    "created_at": "2026-07-14T00:00:00Z",
                    "published_at": "2026-07-14T01:00:00Z",
                    "author": {"login": "benclawbot"},
                }
            ]
        if "/issues?" in path:
            return [
                {
                    "number": 1,
                    "title": "Issue",
                    "state": "open",
                    "user": {"login": "alice"},
                    "assignees": [{"login": "bob"}],
                    "labels": [{"name": "bug"}],
                    "comments": 2,
                    "created_at": "2026-07-14T00:00:00Z",
                    "updated_at": "2026-07-14T01:00:00Z",
                    "closed_at": None,
                },
                {"number": 2, "title": "PR shadow", "state": "open", "pull_request": {}},
            ]
        if "/pulls?" in path:
            return [
                {
                    "number": 2,
                    "title": "PR",
                    "state": "open",
                    "draft": False,
                    "user": {"login": "alice"},
                    "head": {"ref": "feature"},
                    "base": {"ref": "main"},
                    "merge_commit_sha": None,
                    "created_at": "2026-07-14T00:00:00Z",
                    "updated_at": "2026-07-14T01:00:00Z",
                    "closed_at": None,
                    "merged_at": None,
                }
            ]
        if path.endswith("/status"):
            return {"state": "success", "statuses": [{"context": "ci", "state": "success"}]}
        if "/check-runs?" in path:
            return {
                "check_runs": [
                    {
                        "id": 3,
                        "name": "tests",
                        "status": "completed",
                        "conclusion": "success",
                        "started_at": "2026-07-14T00:00:00Z",
                        "completed_at": "2026-07-14T00:01:00Z",
                        "app": {"name": "GitHub Actions"},
                    }
                ]
            }
        raise AssertionError(path)


def repository_state(**overrides):
    values = {
        "id": 1,
        "name": "alpha",
        "full_name": "benclawbot/alpha",
        "path": "/workspace/repositories/alpha",
        "default_branch": "main",
        "head_sha": "abc",
        "visibility": "private",
        "fork": False,
        "archived": False,
        "updated_at": "2026-07-14T00:00:00Z",
        "status": "unchanged",
    }
    values.update(overrides)
    return RepositoryState(**values)


def test_indexes_normalized_repository_metadata(tmp_path):
    github = FakeGitHub()
    state = SyncState(owner="benclawbot", repositories={"1": repository_state()})

    result = GitHubMetadataIndexer(tmp_path, github).build(state)

    assert result.refreshed_count == 1
    assert result.failed_count == 0
    artifact = json.loads((tmp_path / "github" / "repositories" / "1.json").read_text())
    assert artifact["summary"] == {
        "branch_count": 1,
        "check_count": 1,
        "combined_status": "success",
        "issue_count": 1,
        "open_issue_count": 1,
        "open_pull_request_count": 1,
        "pull_request_count": 1,
        "release_count": 1,
        "tag_count": 1,
    }
    assert artifact["issues"][0]["labels"] == ["bug"]
    assert artifact["pull_requests"][0]["head"] == "feature"


def test_reuses_unchanged_repository_artifact(tmp_path):
    github = FakeGitHub()
    state = SyncState(owner="benclawbot", repositories={"1": repository_state()})
    indexer = GitHubMetadataIndexer(tmp_path, github)
    indexer.build(state)
    first_call_count = len(github.calls)

    result = indexer.build(state)

    assert result.reused_count == 1
    assert result.refreshed_count == 0
    assert len(github.calls) == first_call_count


def test_force_refresh_ignores_matching_fingerprint(tmp_path):
    github = FakeGitHub()
    state = SyncState(owner="benclawbot", repositories={"1": repository_state()})
    indexer = GitHubMetadataIndexer(tmp_path, github)
    indexer.build(state)
    first_call_count = len(github.calls)

    result = indexer.build(state, force=True)

    assert result.refreshed_count == 1
    assert len(github.calls) > first_call_count


def test_inaccessible_repository_is_recorded_without_api_calls(tmp_path):
    github = FakeGitHub()
    state = SyncState(
        owner="benclawbot",
        repositories={"1": repository_state(accessible=False, status="removed-or-inaccessible")},
    )

    result = GitHubMetadataIndexer(tmp_path, github).build(state)

    manifest = json.loads(result.index_path.read_text())
    assert result.reused_count == 1
    assert github.calls == []
    assert manifest["repositories"]["1"]["status"] == "unavailable"


def test_one_repository_failure_does_not_abort_manifest(tmp_path):
    github = FakeGitHub()
    github.fail_path = "/releases?"
    state = SyncState(owner="benclawbot", repositories={"1": repository_state()})

    result = GitHubMetadataIndexer(tmp_path, github).build(state)

    manifest = json.loads(result.index_path.read_text())
    assert result.failed_count == 1
    assert manifest["repositories"]["1"]["status"] == "failed"
    assert "RuntimeError: boom" in manifest["repositories"]["1"]["error"]
