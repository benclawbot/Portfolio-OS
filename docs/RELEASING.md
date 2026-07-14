# Releasing Portfolio OS

Portfolio OS releases are produced by `.github/workflows/release.yml`. The workflow is the canonical release path because it reruns the complete verification suite and publishes reproducible build artifacts.

## Manual release

1. Ensure `pyproject.toml` contains the intended version.
2. Ensure `portfolio_os.__version__` matches it.
3. Add a matching `## <version>` section to `CHANGELOG.md`.
4. Ensure CI on `main` is passing.
5. Open **Actions → Release → Run workflow**.
6. Enter the version without the `v` prefix, such as `1.0.0`.
7. Leave the target as `main` unless intentionally releasing another commit.

The workflow then:

- validates the semantic version;
- checks that it matches `pyproject.toml`;
- compiles the package;
- runs Ruff;
- runs the full test suite with coverage;
- builds the wheel and source distribution;
- installs the generated wheel and verifies core commands;
- generates `SHA256SUMS.txt`;
- creates an annotated `v<version>` tag;
- extracts release notes from `CHANGELOG.md`;
- publishes the GitHub Release with all files under `dist/`.

## Tag-triggered release

Pushing a tag matching `v*` also starts the release workflow. The version derived from the tag must exactly match `pyproject.toml`.

```bash
git tag -a v1.0.0 -m "Portfolio OS v1.0.0"
git push origin v1.0.0
```

The manual workflow is preferred because it creates the tag only after verification succeeds.

## Release artifacts

A successful release contains:

- Python wheel;
- source distribution;
- `SHA256SUMS.txt`.

Verify downloaded files with:

```bash
sha256sum --check SHA256SUMS.txt
```

## Failure behavior

No release is published when compilation, linting, tests, build, package installation, version matching, changelog extraction, or tag creation fails.

The workflow refuses to overwrite an existing tag. Correct the release state explicitly rather than force-moving release tags.

## Versioning

Portfolio OS follows semantic versioning from `1.0.0` onward:

- patch: compatible fixes and internal hardening;
- minor: backward-compatible features;
- major: incompatible CLI, API, configuration, or artifact-schema changes.
