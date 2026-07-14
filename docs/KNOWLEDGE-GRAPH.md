# Portfolio Knowledge Graph

Phase 4 stores portfolio evidence as a typed, explainable graph.

## Node types

- `repository`
- `component`
- `technology`
- `capability`
- `workflow`
- `release`

## Relationship types

- `depends-on`
- `consumes`
- `duplicates`
- `supersedes`
- `extracted-from`
- `contains`
- `uses`
- `implements`
- `related-to`

Every inferred edge carries a confidence score and evidence. Human-approved portfolio decisions are marked with `properties.source = decision` and confidence `1.0`.

## Build a graph

```bash
python -m portfolio_os.cli graph-build \
  /path/to/Medusa \
  /path/to/Zeus \
  /path/to/FilesFlow \
  --output reports/latest/portfolio-graph.json
```

Repository nodes are enriched from Phase 1 analysis and Phase 3 DNA. Technical and capability nodes are shared across repositories. Pairwise DNA similarity adds `related-to` edges above the configured threshold and `duplicates` edges only at very high overlap.

## Query neighbors

```bash
python -m portfolio_os.cli graph-query \
  reports/latest/portfolio-graph.json \
  repo:Medusa
```

Use `--incoming` to find consumers or dependants and `--relation` to filter one relationship type.

## Impact analysis

```bash
python -m portfolio_os.cli graph-query \
  reports/latest/portfolio-graph.json \
  repo:Medusa \
  --impact
```

Impact follows incoming relationships breadth-first and reports depth and the relationship used to reach each affected node.

## Relationship paths

```bash
python -m portfolio_os.cli graph-path \
  reports/latest/portfolio-graph.json \
  repo:FilesFlow \
  technology:frameworks:flutter
```

## Safety and limitations

The graph is descriptive and recommendation-oriented. It does not merge, archive, delete, or rewrite repositories. Similarity edges are static-analysis hypotheses, not automatic consolidation decisions. The initial store is deterministic JSON for inspectability and version control; a database backend can be introduced later without changing the public graph model.
