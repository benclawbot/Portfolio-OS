# GitHub synchronization and managed workspace

Portfolio OS can discover every repository owned by the configured GitHub account that is visible to the supplied token, including private repositories, and maintain safe local checkouts under one workspace.

## Authentication

Set a fine-grained token in `GITHUB_TOKEN` or `GH_TOKEN`. It needs read access to repository metadata and contents for every repository that should be discovered. Private repositories omitted by the token are classified as removed or inaccessible on the next run; their local directories are never deleted.

## Commands

```bash
export GITHUB_TOKEN=github_pat_...
python -m portfolio_os.cli sync --pretty
python -m portfolio_os.cli sync --workspace ~/Portfolio-OS-workspace --no-analyze
python -m portfolio_os.cli workspace-status --pretty
```

The managed layout is:

```text
<workspace>/
├── repositories/<repository>/
├── analysis/<repository-id>.json
└── sync-state.json
```

`sync-state.json` is written through a temporary file, flushed, and atomically replaced.

## Safety behavior

- Missing repositories are cloned.
- Existing repositories are fetched with pruning and tags.
- A clean checkout on its default branch may be advanced only with `git merge --ff-only`.
- No reset, checkout, clean, rebase, forced update, branch deletion, or local-directory deletion is performed.
- Dirty working trees are reported and left untouched.
- Clean repositories on another branch or detached HEAD are fetched but not switched.
- Archived repositories are recorded without updating their working trees.
- Workspace path conflicts and mismatched origins are reported without modification.
- Renamed repositories retain their existing local directory when it is safe to identify them by stable GitHub repository ID.
- Repositories missing from discovery remain in state as `removed-or-inaccessible`; local files are preserved.

## Change-driven analysis

Analysis runs only when the remote default-branch HEAD or relevant metadata changed, or when a repository was cloned, restored, or renamed. Unchanged repositories are fetched but not analyzed again. Use `--no-analyze` to perform synchronization only.

## Structured result

The default command output is JSON. Each repository includes stable ID, full name, local path, default branch, HEAD SHA, visibility, fork and archived flags, last GitHub update, dirty/accessibility state, synchronization status, analysis flag, and a safety message when relevant.

Exit code `2` indicates at least one dirty tree, path conflict, or origin mismatch. The state is still persisted so automation can inspect the complete result.
