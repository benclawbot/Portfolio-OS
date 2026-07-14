from __future__ import annotations

import json
import os
import tempfile
import urllib.parse
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Protocol

from portfolio_os.sync import RepositoryState, SyncState


class GitHubMetadataClient(Protocol):
    def _request(self, path: str) -> Any: ...


@dataclass(frozen=True)
class GitHubIndexResult:
    index_path: Path
    repository_count: int
    refreshed_count: int
    reused_count: int
    failed_count: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "index_path": str(self.index_path),
            "repository_count": self.repository_count,
            "refreshed_count": self.refreshed_count,
            "reused_count": self.reused_count,
            "failed_count": self.failed_count,
        }


def _write_json_atomic(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
            json.dump(data, handle, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def _actor(data: Any) -> str | None:
    if not isinstance(data, dict):
        return None
    login = data.get("login")
    return str(login) if login else None


class GitHubMetadataIndexer:
    """Persist normalized GitHub metadata without modifying managed checkouts."""

    schema_version = 1

    def __init__(self, workspace: Path, github: GitHubMetadataClient) -> None:
        self.workspace = workspace.expanduser().resolve()
        self.github = github
        self.root = self.workspace / "github"
        self.repositories_dir = self.root / "repositories"
        self.index_path = self.root / "index.json"

    def build(self, state: SyncState, *, force: bool = False) -> GitHubIndexResult:
        previous = _load_json(self.index_path).get("repositories", {})
        previous = previous if isinstance(previous, dict) else {}
        current: dict[str, dict[str, Any]] = {}
        refreshed = 0
        reused = 0
        failed = 0

        for repository_id in sorted(state.repositories, key=lambda value: int(value)):
            repository = state.repositories[repository_id]
            prior = previous.get(repository_id)
            fingerprint = self._fingerprint(repository)
            artifact_path = self.repositories_dir / f"{repository_id}.json"

            if (
                not force
                and isinstance(prior, dict)
                and prior.get("fingerprint") == fingerprint
                and artifact_path.exists()
            ):
                current[repository_id] = prior
                reused += 1
                continue

            if not repository.accessible:
                current[repository_id] = self._manifest_entry(repository, fingerprint, artifact_path, "unavailable")
                reused += 1
                continue

            try:
                artifact = self._collect(repository)
                _write_json_atomic(artifact_path, artifact)
                current[repository_id] = self._manifest_entry(repository, fingerprint, artifact_path, "indexed")
                refreshed += 1
            except Exception as error:
                failed += 1
                entry = self._manifest_entry(repository, fingerprint, artifact_path, "failed")
                entry["error"] = f"{type(error).__name__}: {error}"
                current[repository_id] = entry

        indexed_at = datetime.now(timezone.utc).isoformat()
        manifest = {
            "schema_version": self.schema_version,
            "owner": state.owner,
            "indexed_at": indexed_at,
            "summary": {
                "repository_count": len(current),
                "refreshed_count": refreshed,
                "reused_count": reused,
                "failed_count": failed,
            },
            "repositories": current,
        }
        _write_json_atomic(self.index_path, manifest)
        return GitHubIndexResult(self.index_path, len(current), refreshed, reused, failed)

    def _fingerprint(self, repository: RepositoryState) -> str:
        return "|".join(
            (
                repository.full_name,
                repository.default_branch,
                repository.head_sha or "",
                repository.updated_at or "",
                str(repository.archived),
                str(repository.accessible),
            )
        )

    def _manifest_entry(
        self,
        repository: RepositoryState,
        fingerprint: str,
        artifact_path: Path,
        status: str,
    ) -> dict[str, Any]:
        return {
            "id": repository.id,
            "full_name": repository.full_name,
            "fingerprint": fingerprint,
            "status": status,
            "artifact_path": str(artifact_path),
        }

    def _pages(self, path: str, **params: Any) -> list[dict[str, Any]]:
        page = 1
        result: list[dict[str, Any]] = []
        while True:
            query = urllib.parse.urlencode({**params, "per_page": 100, "page": page})
            payload = self.github._request(f"{path}?{query}")
            if not isinstance(payload, list):
                raise TypeError(f"GitHub API returned a non-list payload for {path}")
            result.extend(item for item in payload if isinstance(item, dict))
            if len(payload) < 100:
                return result
            page += 1

    def _collect(self, repository: RepositoryState) -> dict[str, Any]:
        base = f"/repos/{repository.full_name}"
        branches = self._pages(f"{base}/branches", protected="false")
        tags = self._pages(f"{base}/tags")
        releases = self._pages(f"{base}/releases")
        issues_payload = self._pages(f"{base}/issues", state="all", sort="updated", direction="desc")
        pulls = self._pages(f"{base}/pulls", state="all", sort="updated", direction="desc")
        issues = [item for item in issues_payload if "pull_request" not in item]

        status_payload: dict[str, Any] = {}
        checks_payload: dict[str, Any] = {}
        if repository.head_sha:
            status = self.github._request(f"{base}/commits/{repository.head_sha}/status")
            checks = self.github._request(f"{base}/commits/{repository.head_sha}/check-runs?per_page=100")
            status_payload = status if isinstance(status, dict) else {}
            checks_payload = checks if isinstance(checks, dict) else {}

        normalized_branches = [
            {
                "name": str(item.get("name", "")),
                "sha": str(item.get("commit", {}).get("sha", "")),
                "protected": bool(item.get("protected", False)),
            }
            for item in branches
        ]
        normalized_tags = [
            {
                "name": str(item.get("name", "")),
                "sha": str(item.get("commit", {}).get("sha", "")),
            }
            for item in tags
        ]
        normalized_releases = [
            {
                "id": int(item.get("id", 0)),
                "tag_name": str(item.get("tag_name", "")),
                "name": item.get("name"),
                "draft": bool(item.get("draft", False)),
                "prerelease": bool(item.get("prerelease", False)),
                "created_at": item.get("created_at"),
                "published_at": item.get("published_at"),
                "author": _actor(item.get("author")),
            }
            for item in releases
        ]
        normalized_issues = [self._issue(item) for item in issues]
        normalized_pulls = [self._pull(item) for item in pulls]
        normalized_checks = [
            {
                "id": int(item.get("id", 0)),
                "name": str(item.get("name", "")),
                "status": item.get("status"),
                "conclusion": item.get("conclusion"),
                "started_at": item.get("started_at"),
                "completed_at": item.get("completed_at"),
                "app": str(item.get("app", {}).get("name", "")) or None,
            }
            for item in checks_payload.get("check_runs", [])
            if isinstance(item, dict)
        ]

        return {
            "schema_version": self.schema_version,
            "repository": {
                "id": repository.id,
                "full_name": repository.full_name,
                "default_branch": repository.default_branch,
                "head_sha": repository.head_sha,
                "visibility": repository.visibility,
                "archived": repository.archived,
            },
            "indexed_at": datetime.now(timezone.utc).isoformat(),
            "summary": {
                "branch_count": len(normalized_branches),
                "tag_count": len(normalized_tags),
                "release_count": len(normalized_releases),
                "issue_count": len(normalized_issues),
                "open_issue_count": sum(item["state"] == "open" for item in normalized_issues),
                "pull_request_count": len(normalized_pulls),
                "open_pull_request_count": sum(item["state"] == "open" for item in normalized_pulls),
                "check_count": len(normalized_checks),
                "combined_status": status_payload.get("state"),
            },
            "branches": normalized_branches,
            "tags": normalized_tags,
            "releases": normalized_releases,
            "issues": normalized_issues,
            "pull_requests": normalized_pulls,
            "checks": {
                "combined_state": status_payload.get("state"),
                "statuses": status_payload.get("statuses", []),
                "runs": normalized_checks,
            },
        }

    def _issue(self, item: dict[str, Any]) -> dict[str, Any]:
        return {
            "number": int(item.get("number", 0)),
            "title": str(item.get("title", "")),
            "state": str(item.get("state", "")),
            "state_reason": item.get("state_reason"),
            "author": _actor(item.get("user")),
            "assignees": [_actor(actor) for actor in item.get("assignees", []) if _actor(actor)],
            "labels": [
                str(label.get("name", ""))
                for label in item.get("labels", [])
                if isinstance(label, dict) and label.get("name")
            ],
            "comments": int(item.get("comments", 0)),
            "created_at": item.get("created_at"),
            "updated_at": item.get("updated_at"),
            "closed_at": item.get("closed_at"),
        }

    def _pull(self, item: dict[str, Any]) -> dict[str, Any]:
        return {
            "number": int(item.get("number", 0)),
            "title": str(item.get("title", "")),
            "state": str(item.get("state", "")),
            "draft": bool(item.get("draft", False)),
            "author": _actor(item.get("user")),
            "head": str(item.get("head", {}).get("ref", "")),
            "base": str(item.get("base", {}).get("ref", "")),
            "merge_commit_sha": item.get("merge_commit_sha"),
            "created_at": item.get("created_at"),
            "updated_at": item.get("updated_at"),
            "closed_at": item.get("closed_at"),
            "merged_at": item.get("merged_at"),
        }
