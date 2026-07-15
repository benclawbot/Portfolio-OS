# Medusa execution integration

Portfolio OS 1.2 adds an explicit, auditable boundary between portfolio governance and autonomous implementation.

Portfolio OS never executes generated recommendations automatically. A recommendation must first be accepted into a durable execution request. Only then may it be passed to Medusa.

## Accept a recommendation

```bash
portfolio-backlog --pretty
portfolio-execute accept rec-0123456789ab
```

Acceptance validates that:

- the recommendation exists in the current generated backlog;
- its repository exists in the synchronized workspace;
- the checkout is a real Git repository;
- the repository is accessible and not archived;
- the managed working tree is not marked dirty.

The request is written to:

```text
<workspace>/execution/requests/<execution-id>.json
```

It contains the original evidence, acceptance criteria and verification plan, plus a bounded Medusa objective that instructs the agent to work only inside the selected repository and preserve unrelated changes.

## Execute with Medusa

```bash
portfolio-execute execute exec-0123456789abcdef
```

Portfolio OS launches:

```text
medusa --repo <managed-repository-path> run <bounded-objective>
```

The command is executed with the repository itself as the working directory. Portfolio OS does not pass shell interpolation through a command string.

## Verification receipts

Medusa completion output is captured as an immutable receipt:

```text
<workspace>/execution/receipts/<execution-id>.json
```

The receipt records:

- request and recommendation IDs;
- repository identity;
- exact argument vector;
- timestamps and exit code;
- stdout and stderr;
- verification lines emitted as `evidence: ...`;
- SHA-256 of the accepted execution request.

A zero exit code produces `completed`; all other exit codes produce `failed`. Failed runs are retained rather than overwritten or hidden.

## Inspect requests and receipts

```bash
portfolio-execute requests
portfolio-execute receipts
```

## Safety properties

- Generated backlog items are proposals, not executable instructions.
- Acceptance and execution are separate explicit operations.
- Dirty, archived, inaccessible or unmanaged repositories are rejected.
- Execution is repository-scoped through Medusa's `--repo` boundary.
- Requests and receipts are written atomically.
- The accepted request is checksummed in the receipt.
- Portfolio OS does not claim that acceptance criteria passed merely because Medusa exited successfully; verification evidence remains visible for review and the next portfolio refresh supplies independent scoring.

The closed loop is:

```text
Portfolio OS evidence
→ generated recommendation
→ explicit acceptance
→ bounded Medusa execution
→ durable verification receipt
→ Portfolio OS refresh and independent reassessment
```
