# Evidence-based README generator

Phase 2 converts Phase 1 repository facts into deterministic Markdown without inventing product capabilities.

## Safety contract

- Existing leading hero banners are preserved exactly by default.
- Existing README body copy is not reused as evidence.
- Generation stops when any analyzer fails.
- Output is deterministic and contains no generated timestamp.
- Replacing `README.md` requires explicit `--write`.
- Writes are atomic through a temporary file and `os.replace`.

## Commands

Preview generated Markdown:

```bash
python -m portfolio_os.cli readme /path/to/repository
```

Show a unified diff:

```bash
python -m portfolio_os.cli readme /path/to/repository --diff
```

Write a candidate elsewhere:

```bash
python -m portfolio_os.cli readme /path/to/repository \
  --output reports/latest/README.candidate.md
```

Check for drift without modifying files:

```bash
python -m portfolio_os.cli readme /path/to/repository --check
```

`--check` exits with code `2` when the current README differs from generated evidence.

Replace the README atomically:

```bash
python -m portfolio_os.cli readme /path/to/repository --write
```

Use `--no-preserve-hero` only when the existing visual must be removed.

## Evidence sources

The generator currently uses:

- project metadata from `pyproject.toml`, `package.json`, and `Cargo.toml`,
- languages and frameworks detected by Phase 1,
- manifests and lockfiles,
- manifest-defined commands,
- repository entry points and top-level directories,
- detected test files,
- GitHub Actions workflow paths,
- the presence of a license file.

## Generated sections

Sections are included only when supporting evidence exists:

- overview,
- repository evidence,
- technology stack,
- repository structure,
- installation,
- available commands,
- testing,
- documentation scope,
- license.

## Current limitations

Phase 2 does not yet infer domain-specific features from source symbols, execute commands, inspect screenshots, generate badges, or push changes across remote repositories. Those require the GitHub acquisition and deeper semantic-analysis layers.
