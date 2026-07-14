from __future__ import annotations

import json
import os
import subprocess
import tempfile
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Protocol


class SyncError(RuntimeError):
    """Raised when repository synchronization cannot complete safely."""


@dataclass(frozen=True)
class RemoteRepository:
    id: int
    name: str
    full_name: str
    clone_url: str
    default_branch: str
    head_sha: str | None
    visibility: str
    fork: bool
    archived: bool
    updated_at: str | None

    @classmethod
    def from_api(cls, data: dict[str, Any], head_sha: str | None = None) -> "RemoteRepository":
        return cls(
            id=int(data["id"]),
            name=str(data["name"]),
            full_name=str(data["full_name"]),
            clone_url=str(data["clone_url"]),
            default_branch=str(data.get("default_branch") or "main"),
            head_sha=head_sha,
            visibility=str(data.get("visibility") or ("private" if data.get("private") else "public")),
            fork=bool(data.get("fork", False)),
            archived=bool(data.get("archived", False)),
            updated_at=data.get("updated_at"),
        )


@dataclass
class RepositoryState:
    id: int
    name: str
    full_name: str
    path: str
    default_branch: str
    head_sha: str | None
    visibility: str
    fork: bool
    archived: bool
    updated_at: str | None
    status: str
    dirty: bool = False
    accessible: bool = True
    analyzed: bool = False
    message: str | None = None


@dataclass
class SyncState:
    schema_version: int = 1
    owner: str = ""
    synchronized_at: str = ""
    repositories: dict[str, RepositoryState] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "owner": self.owner,
            "synchronized_at": self.synchronized_at,
            "repositories": {key: asdict(value) for key, value in sorted(self.repositories.items())},
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SyncState":
        repositories = {key: RepositoryState(**value) for key, value in data.get("repositories", {}).items()}
        return cls(
            schema_version=int(data.get("schema_version", 1)),
            owner=str(data.get("owner", "")),
            synchronized_at=str(data.get("synchronized_at", "")),
            repositories=repositories,
        )


@dataclass(frozen=True)
class SyncResult:
    state_path: Path
    repositories: tuple[RepositoryState, ...]

    def to_dict(self) -> dict[str, Any]:
        counts: dict[str, int] = {}
        for repository in self.repositories:
            counts[repository.status] = counts.get(repository.status, 0) + 1
        return {
            "state_path": str(self.state_path),
            "summary": {
                "repository_count": len(self.repositories),
                "analyzed_count": sum(item.analyzed for item in self.repositories),
                "dirty_count": sum(item.dirty for item in self.repositories),
                "status_counts": counts,
            },
            "repositories": [asdict(item) for item in self.repositories],
        }


class GitHubClient(Protocol):
    def repositories(self, owner: str) -> Iterable[RemoteRepository]: ...


class GitClient(Protocol):
    def clone(self, clone_url: str, destination: Path) -> None: ...
    def fetch(self, repository: Path) -> None: ...
    def is_dirty(self, repository: Path) -> bool: ...
    def current_branch(self, repository: Path) -> str | None: ...
    def local_head(self, repository: Path) -> str | None: ...
    def fast_forward_default(self, repository: Path, default_branch: str) -> bool: ...
    def remote_url(self, repository: Path) -> str | None: ...


class GitHubAPIClient:
    def __init__(self, token: str | None = None, api_url: str = "https://api.github.com") -> None:
        self.token = token or os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
        if not self.token:
            raise SyncError("GitHub authentication requires GITHUB_TOKEN or GH_TOKEN")
        self.api_url = api_url.rstrip("/")

    def _request(self, path: str) -> Any:
        request = urllib.request.Request(
            f"{self.api_url}{path}",
            headers={
                "Accept": "application/vnd.github+json",
                "Authorization": f"Bearer {self.token}",
                "X-GitHub-Api-Version": "2022-11-28",
                "User-Agent": "portfolio-os",
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                return json.load(response)
        except urllib.error.HTTPError as error:
            raise SyncError(f"GitHub API request failed ({error.code}) for {path}") from error
        except urllib.error.URLError as error:
            raise SyncError(f"GitHub API request failed for {path}: {error.reason}") from error

    def repositories(self, owner: str) -> Iterable[RemoteRepository]:
        page = 1
        while True:
            query = urllib.parse.urlencode(
                {"affiliation": "owner,collaborator,organization_member", "per_page": 100, "page": page}
            )
            payload = self._request(f"/user/repos?{query}")
            if not payload:
                break
            for item in payload:
                if item.get("owner", {}).get("login", "").lower() != owner.lower():
                    continue
                branch = urllib.parse.quote(str(item.get("default_branch") or "main"), safe="")
                try:
                    branch_data = self._request(f"/repos/{item['full_name']}/branches/{branch}")
                    head_sha = branch_data.get("commit", {}).get("sha")
                except SyncError:
                    head_sha = None
                yield RemoteRepository.from_api(item, head_sha=head_sha)
            if len(payload) < 100:
                break
            page += 1


class SubprocessGitClient:
    def _run(
        self, args: list[str], cwd: Path | None = None, check: bool = True
    ) -> subprocess.CompletedProcess[str]:
        result = subprocess.run(["git", *args], cwd=cwd, text=True, capture_output=True, check=False)
        if check and result.returncode:
            detail = result.stderr.strip() or result.stdout.strip() or "unknown git error"
            raise SyncError(f"git {' '.join(args)} failed: {detail}")
        return result

    def clone(self, clone_url: str, destination: Path) -> None:
        destination.parent.mkdir(parents=True, exist_ok=True)
        self._run(["clone", "--origin", "origin", "--", clone_url, str(destination)])

    def fetch(self, repository: Path) -> None:
        self._run(["fetch", "--prune", "--tags", "origin"], cwd=repository)

    def is_dirty(self, repository: Path) -> bool:
        return bool(self._run(["status", "--porcelain"], cwd=repository).stdout.strip())

    def current_branch(self, repository: Path) -> str | None:
        result = self._run(["symbolic-ref", "--quiet", "--short", "HEAD"], cwd=repository, check=False)
        return result.stdout.strip() or None

    def local_head(self, repository: Path) -> str | None:
        result = self._run(["rev-parse", "HEAD"], cwd=repository, check=False)
        return result.stdout.strip() or None

    def fast_forward_default(self, repository: Path, default_branch: str) -> bool:
        if self.current_branch(repository) != default_branch:
            return False
        result = self._run(["merge", "--ff-only", f"origin/{default_branch}"], cwd=repository, check=False)
        return result.returncode == 0

    def remote_url(self, repository: Path) -> str | None:
        result = self._run(["remote", "get-url", "origin"], cwd=repository, check=False)
        return result.stdout.strip() or None


def load_state(path: Path) -> SyncState:
    if not path.exists():
        return SyncState()
    return SyncState.from_dict(json.loads(path.read_text(encoding="utf-8")))


def save_state_atomic(state: SyncState, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
            json.dump(state.to_dict(), handle, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


class WorkspaceSynchronizer:
    def __init__(
        self,
        workspace: Path,
        owner: str,
        github: GitHubClient,
        git: GitClient,
        analyzer: Any | None = None,
    ) -> None:
        self.workspace = workspace.expanduser().resolve()
        self.owner = owner
        self.github = github
        self.git = git
        self.analyzer = analyzer
        self.repositories_dir = self.workspace / "repositories"
        self.state_path = self.workspace / "sync-state.json"
        self.analysis_dir = self.workspace / "analysis"

    def synchronize(self, analyze_changed: bool = True) -> SyncResult:
        previous = load_state(self.state_path)
        remotes = list(self.github.repositories(self.owner))
        by_id = {item.id: item for item in previous.repositories.values()}
        current: dict[str, RepositoryState] = {}
        seen_ids: set[int] = set()

        for remote in sorted(remotes, key=lambda item: item.full_name.lower()):
            seen_ids.add(remote.id)
            prior = by_id.get(remote.id)
            path = self.repositories_dir / remote.name
            status = "unchanged"
            message = None
            dirty = False
            analyzed = False

            if prior and prior.full_name != remote.full_name:
                status = "renamed"
                old_path = Path(prior.path)
                if old_path.exists() and not path.exists():
                    path = old_path
                    message = f"Repository renamed from {prior.full_name}; existing directory retained"
            metadata_changed = prior is None or any(
                (
                    prior.default_branch != remote.default_branch,
                    prior.visibility != remote.visibility,
                    prior.fork != remote.fork,
                    prior.archived != remote.archived,
                    prior.updated_at != remote.updated_at,
                )
            )
            head_changed = prior is None or prior.head_sha != remote.head_sha

            if remote.archived:
                status = "archived" if status == "unchanged" else status
                message = message or "Archived repository recorded without updating its working tree"
            elif not path.exists():
                self.git.clone(remote.clone_url, path)
                status = "cloned" if prior is None else "restored"
            elif not (path / ".git").exists():
                status = "path-conflict"
                message = "Workspace path exists but is not a Git repository"
            else:
                dirty = self.git.is_dirty(path)
                remote_url = self.git.remote_url(path)
                if remote_url and remote.name.lower() not in remote_url.lower():
                    status = "remote-mismatch"
                    message = f"Origin does not appear to match {remote.full_name}"
                elif dirty:
                    status = "dirty"
                    message = "Dirty working tree left untouched"
                else:
                    self.git.fetch(path)
                    if head_changed:
                        if self.git.fast_forward_default(path, remote.default_branch):
                            status = "updated" if status == "unchanged" else status
                        else:
                            status = "fetched"
                            message = "Fetched remote changes without changing the checked-out branch"
                    elif metadata_changed and status == "unchanged":
                        status = "metadata-changed"

            should_analyze = (
                analyze_changed
                and self.analyzer is not None
                and not remote.archived
                and status not in {"dirty", "path-conflict", "remote-mismatch"}
                and (head_changed or metadata_changed or status in {"cloned", "restored", "renamed"})
            )
            if should_analyze:
                analysis = self.analyzer.analyze(path)
                output = self.analysis_dir / f"{remote.id}.json"
                output.parent.mkdir(parents=True, exist_ok=True)
                if hasattr(analysis, "write_json"):
                    analysis.write_json(output)
                else:
                    output.write_text(json.dumps(analysis, indent=2) + "\n", encoding="utf-8")
                analyzed = True

            current[str(remote.id)] = RepositoryState(
                id=remote.id,
                name=remote.name,
                full_name=remote.full_name,
                path=str(path),
                default_branch=remote.default_branch,
                head_sha=remote.head_sha,
                visibility=remote.visibility,
                fork=remote.fork,
                archived=remote.archived,
                updated_at=remote.updated_at,
                status=status,
                dirty=dirty,
                analyzed=analyzed,
                message=message,
            )

        for repository_id, prior in previous.repositories.items():
            if prior.id in seen_ids:
                continue
            prior.status = "removed-or-inaccessible"
            prior.accessible = False
            prior.analyzed = False
            prior.message = "Repository was not returned by GitHub discovery; local files were preserved"
            current[repository_id] = prior

        state = SyncState(
            owner=self.owner,
            synchronized_at=datetime.now(timezone.utc).isoformat(),
            repositories=current,
        )
        save_state_atomic(state, self.state_path)
        return SyncResult(self.state_path, tuple(current[key] for key in sorted(current)))
