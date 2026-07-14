# Portfolio Decisions

## Repository governance

- Portfolio OS repository name: `Portfolio-OS`.
- Visibility: private.
- Includes public and private repositories in its inventory.
- Contains governance documentation and Python automation.
- Feature freeze is recorded only here, not as notices in every repository.
- Open PRs are analyzed and recommendations recorded; no PR mutations are performed during inventory.
- Archive actions are proposal-only until separately approved.

## Medusa consolidation

- Medusa is the canonical agent runtime and product.
- Zeus contributes only its frontend GUI, migrated as `Medusa Desktop` inside Medusa.
- After migration, parity verification, and rollback preparation, the Zeus repository is to be deleted.
- `skills` moves inside Medusa.
- `agent-commit` may be merged into Medusa.
- Useful concepts from Omni-Memory, open-brain, context-mode, and hermes-lcm move into Medusa; none remain active long term.
- Useful concepts from FastBot, autonomos, and AI-Harness are extracted before proposed archival.
- Claude-Harness and Pi-Agent-Optimus remain active.

## Other products

- WebSend remains a separate repository and product.
- FilesFlow integrates with WebSend rather than absorbing it.
- Fork/reference repositories remain public and must clearly identify provenance and upstream.

## Documentation automation

- Apply standards to every active repository.
- Regenerate READMEs from code and configuration.
- Preserve existing hero banners.
- Commit validated README updates directly to `main`.
- Never document aspirational features as implemented.
