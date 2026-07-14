# Portfolio dashboard

Portfolio OS can generate a self-contained static dashboard from the latest portfolio report and optional trend artifacts.

```bash
portfolio-dashboard --pretty
portfolio-dashboard --workspace ~/Portfolio-OS-workspace
portfolio-dashboard --output-dir public
```

The default output is:

```text
<workspace>/dashboard/
├── index.html
└── dashboard-data.json
```

## Evidence sources

The dashboard reads:

- `<workspace>/portfolio/portfolio-summary.json` — required;
- `<workspace>/trends/portfolio-trends.json` — optional.

Missing trend data produces a valid current-state dashboard with an explicit no-history message. Missing portfolio summary data fails clearly because the dashboard never substitutes mock content.

## Dashboard content

The generated page includes:

- repository, active, finding, dirty and inaccessible counts;
- analysis coverage;
- analysis-coverage history rendered as inline SVG;
- language distribution;
- regression signals;
- attention-queue counts;
- a repository table containing synchronization status, primary language, tests and findings.

## Portability and security

`index.html` has no external dependencies, remote fonts, scripts, trackers or network calls. CSS, charts and data-derived content are embedded in the generated file. Repository names and other artifact strings are HTML-escaped before rendering.

`dashboard-data.json` preserves the exact portfolio and trend payloads used to build the page for inspection or downstream integration.

All writes use temporary files, `fsync` and atomic replacement. Dashboard generation does not modify synchronized repositories, history or analysis artifacts.
