# Portfolio OS

Private governance and automation system for the `benclawbot` GitHub portfolio.

## Mission

Portfolio OS inventories repositories, scores health, detects overlap, regenerates evidence-based READMEs while preserving hero banners, tracks migrations, and recommends the highest-value improvements across the portfolio.

## Safety defaults

- Archive and deletion actions are recommendation-only.
- Open pull requests are analyzed but not modified.
- README automation must preserve existing hero banners.
- README claims must be supported by code, tests, configuration, or released artifacts.
- Active-repository README updates are intended to commit directly to `main` after automated validation.

## Current strategic decisions

- Medusa is the canonical coding-agent platform.
- Zeus GUI migrates into Medusa as **Medusa Desktop**; the Zeus repository is deleted only after verified migration.
- Skills, agent-commit, and useful memory/context concepts move into Medusa.
- Claude-Harness and Pi-Agent-Optimus remain active.
- FastBot, autonomos, and AI-Harness are archive candidates after extraction.
- WebSend remains a standalone product.

See `docs/PORTFOLIO-STATUS.md` and `docs/DECISIONS.md`.
