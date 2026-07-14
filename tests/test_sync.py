from portfolio_os.sync import RemoteRepository, SyncState, WorkspaceSynchronizer, load_state, save_state_atomic


class FakeGitHub:
    def __init__(self, repositories):
        self._repositories = repositories

    def repositories(self, owner):
        return self._repositories


class FakeGit:
    def __init__(self):
        self.calls = []
        self.dirty = set()

    def clone(self, clone_url, destination):
        self.calls.append(("clone", destination.name))
        (destination / ".git").mkdir(parents=True)

    def fetch(self, repository):
        self.calls.append(("fetch", repository.name))

    def is_dirty(self, repository):
        return repository.name in self.dirty

    def current_branch(self, repository):
        return "main"

    def local_head(self, repository):
        return "local"

    def fast_forward_default(self, repository, default_branch):
        self.calls.append(("ff", repository.name))
        return True

    def remote_url(self, repository):
        return f"https://github.com/benclawbot/{repository.name}.git"


class FakeAnalysis:
    def write_json(self, path):
        path.write_text('{"ok": true}\n', encoding="utf-8")


class FakeAnalyzer:
    def __init__(self):
        self.paths = []

    def analyze(self, path):
        self.paths.append(path)
        return FakeAnalysis()


def repo(repo_id=1, name="alpha", sha="a", **kwargs):
    return RemoteRepository(
        repo_id,
        name,
        f"benclawbot/{name}",
        f"https://github.com/benclawbot/{name}.git",
        "main",
        sha,
        "private",
        False,
        kwargs.get("archived", False),
        "2026-07-14T00:00:00Z",
    )


def test_clones_and_analyzes_changed_repository(tmp_path):
    git = FakeGit()
    analyzer = FakeAnalyzer()
    result = WorkspaceSynchronizer(tmp_path, "benclawbot", FakeGitHub([repo()]), git, analyzer).synchronize()
    assert result.repositories[0].status == "cloned"
    assert result.repositories[0].analyzed is True
    assert git.calls == [("clone", "alpha")]
    assert (tmp_path / "analysis" / "1.json").exists()


def test_dirty_repository_is_not_fetched_or_analyzed(tmp_path):
    path = tmp_path / "repositories" / "alpha"
    (path / ".git").mkdir(parents=True)
    git = FakeGit()
    git.dirty.add("alpha")
    analyzer = FakeAnalyzer()
    result = WorkspaceSynchronizer(tmp_path, "benclawbot", FakeGitHub([repo()]), git, analyzer).synchronize()
    assert result.repositories[0].status == "dirty"
    assert git.calls == []
    assert analyzer.paths == []


def test_unchanged_repository_is_not_reanalyzed(tmp_path):
    path = tmp_path / "repositories" / "alpha"
    (path / ".git").mkdir(parents=True)
    prior = WorkspaceSynchronizer(tmp_path, "benclawbot", FakeGitHub([repo()]), FakeGit()).synchronize(
        analyze_changed=False
    )
    assert prior.repositories[0].status == "updated"
    analyzer = FakeAnalyzer()
    git = FakeGit()
    result = WorkspaceSynchronizer(tmp_path, "benclawbot", FakeGitHub([repo()]), git, analyzer).synchronize()
    assert result.repositories[0].status == "unchanged"
    assert analyzer.paths == []
    assert git.calls == [("fetch", "alpha")]


def test_removed_repository_is_preserved_in_state(tmp_path):
    path = tmp_path / "repositories" / "alpha"
    (path / ".git").mkdir(parents=True)
    sync = WorkspaceSynchronizer(tmp_path, "benclawbot", FakeGitHub([repo()]), FakeGit())
    sync.synchronize(analyze_changed=False)
    result = WorkspaceSynchronizer(tmp_path, "benclawbot", FakeGitHub([]), FakeGit()).synchronize()
    assert result.repositories[0].status == "removed-or-inaccessible"
    assert result.repositories[0].accessible is False
    assert path.exists()


def test_atomic_state_round_trip(tmp_path):
    path = tmp_path / "state.json"
    state = SyncState(owner="benclawbot")
    save_state_atomic(state, path)
    assert load_state(path).owner == "benclawbot"
    assert not list(tmp_path.glob("*.tmp"))
