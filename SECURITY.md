# Security policy

## Supported versions

Portfolio OS follows semantic versioning from `1.0.0` onward. Security fixes are applied to the latest stable release line. Older experimental pre-1.0 artifacts are not supported.

## Reporting a vulnerability

Do not open a public issue containing exploit details, credentials, private repository names, access tokens, local paths, or portfolio evidence.

For this private repository, report suspected vulnerabilities directly to the repository owner through a private GitHub communication channel. Include:

- the affected Portfolio OS version or commit;
- the affected command, module, or artifact;
- reproduction steps using sanitized data;
- the expected and observed behavior;
- the security impact;
- any proposed mitigation.

Never include live GitHub tokens, private repository contents, or user workspace artifacts in a report.

## Security-sensitive areas

Changes in these areas require particular review:

- GitHub token and Git credential handling;
- repository synchronization and subprocess execution;
- path construction and workspace boundaries;
- analyzer plugins and entry points;
- README or artifact generation from untrusted repository content;
- policy-file and JSON parsing;
- lock handling and stale-lock cleanup;
- release workflows and GitHub Actions permissions.

## Response principles

Security reports should be validated against the current `main` branch. Confirmed issues should receive:

- a severity assessment;
- a minimally scoped fix;
- regression tests where practical;
- a changelog entry;
- a patch release when the stable release is affected.

Portfolio OS must preserve its safety contract while fixing issues: no destructive Git operations, no force-moving published release tags, and no exposure of private portfolio evidence.
