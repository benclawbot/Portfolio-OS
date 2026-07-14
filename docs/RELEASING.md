# Releasing Portfolio OS

Portfolio OS releases are produced only by `.github/workflows/release.yml`. The workflow is the canonical release path because it reruns the complete verification suite before creating a tag or publishing artifacts.

## Release procedure

1. Ensure `pyproject.toml` contains the intended version.
2. Ensure `portfolio_os.__version__` matches it.
3. Add a matching `## <version>` section to `CHANGELOG.md`.
4. Ensure CI on `main` is passing.
5. Open **Actions → Release → Run workflow**.
6. Enter the version without the `v` prefix, such as `1.0.0`.
7. Leave the target as `main` unless intentionally releasing another commit.

The workflow then:

- validates the semantic version;
- checks both package version declarations;
- verifies a matching changelog section;
- compiles the package;
- runs Ruff;
- runs the full test suite with coverage;
- builds the wheel and source distribution;
- installs the generated wheel and verifies core commands;
- generates `SHA256SUMS.txt`;
- verifies that the release tag does not already exist remotely;
- creates and pushes an annotated `v<version>` tag;
- extracts release notes from `CHANGELOG.md`;
- publishes the GitHub Release with all files under `dist/`.

The workflow uses a per-version concurrency group, so the same version cannot be released by overlapping runs.

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

No tag or release is created when version validation, compilation, linting, tests, build, package installation, command verification, or changelog validation fails.

The workflow refuses to overwrite an existing remote tag. Correct the release state explicitly rather than force-moving release tags.

A failure after the tag is pushed but before GitHub Release publication leaves the immutable tag in place. Diagnose the failed step and publish against that existing tag manually rather than deleting or moving it without review.

## Versioning

Portfolio OS follows semantic versioning from `1.0.0` onward:

- patch: compatible fixes and internal hardening;
- minor: backward-compatible features;
- major: incompatible CLI, API, configuration, or artifact-schema changes.
