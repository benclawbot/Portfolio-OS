from __future__ import annotations

import os


def configure_git_auth() -> None:
    """Expose a GitHub token to child Git processes without persisting credentials."""
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if not token:
        return
    os.environ.setdefault("GIT_CONFIG_COUNT", "1")
    os.environ.setdefault("GIT_CONFIG_KEY_0", "http.extraHeader")
    os.environ.setdefault("GIT_CONFIG_VALUE_0", f"Authorization: Bearer {token}")
