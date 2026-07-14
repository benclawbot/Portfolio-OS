# Repository DNA

Phase 3 turns Phase 1 repository facts into deterministic fingerprints and explainable similarity scores.

## Commands

Generate DNA for one checkout:

```bash
python -m portfolio_os.cli dna /path/to/repository
```

Write the fingerprint to a file:

```bash
python -m portfolio_os.cli dna /path/to/repository \
  --output reports/latest/repository-dna.json
```

Compare two checkouts:

```bash
python -m portfolio_os.cli compare /path/to/repo-a /path/to/repo-b --pretty
```

Write a complete machine-readable comparison:

```bash
python -m portfolio_os.cli compare /path/to/repo-a /path/to/repo-b \
  --output reports/latest/comparison.json
```

## Fingerprint dimensions

Repository DNA currently contains normalized evidence for:

- languages,
- build ecosystems,
- frameworks,
- dependencies,
- manifest-defined commands,
- top-level directories,
- entry points,
- inferred capabilities.

The fingerprint is a SHA-256 digest of canonical JSON. Repository paths, timestamps, findings, and mutable presentation data are excluded, so identical evidence produces the same fingerprint.

## Similarity model

Similarity uses weighted Jaccard overlap. Dependencies and capabilities receive the highest weight, while languages alone contribute relatively little. Empty dimensions are ignored and the remaining active weights are normalized.

Classifications:

| Score | Classification |
|---:|---|
| 75–100% | very-high-overlap |
| 55–74.99% | high-overlap |
| 35–54.99% | related |
| 18–34.99% | weakly-related |
| below 18% | distinct |

Every result includes per-dimension overlap, values unique to each repository, and up to three human-readable reasons.

## Safety and limitations

Repository DNA is evidence for review, not an automatic merge or archive decision. Similar technology stacks do not prove duplicate product purpose. Phase 3 does not yet compare source symbols, API contracts, embeddings, copied code, Git history, or runtime behavior. These signals will be added by later portfolio graph and semantic-analysis phases.
