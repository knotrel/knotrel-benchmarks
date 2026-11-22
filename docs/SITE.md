# Performance website

The static site is served directly from this directory, without Jekyll, Node,
external fonts or runtime dependencies. Existing methodology and research files
are preserved. The site uses Knotrel's mark and a distinct violet accent.

## Build and preview

```sh
python3 scripts/build_site.py
python3 scripts/build_site.py --check
python3 -m unittest discover -s scripts/tests -p 'test_build_site.py'
python3 -m http.server 8000 --directory docs
```

Open http://localhost:8000. All navigation works under the GitHub project prefix
`/knotrel-benchmarks/` as well as at a domain root. No benchmark runs during build.

## GitHub Pages

After these changes are committed and pushed, select **Settings > Pages > Deploy
from a branch**, choose the branch containing the site (normally `main`), and
select **/docs**. The expected project URL is
https://knotrel.github.io/knotrel-benchmarks/. No deployment workflow is required.

## Publishing evidence

`docs/data/releases.json` is the source for release pages; the Python generator
owns the HTML pages. Add an adapter/export from a campaign analyzer rather than
manually transcribing measurements. This initial site intentionally contains
only a planned 1.0.0 report, with no fabricated values or verdicts.

For 1.0.0, freeze the latest released 0.9.x patch as an exact tag and 40-character
SHA. Later updates must not change the selected reference retrospectively.

A published entry needs `version`, `status: published`, `baseline_policy`, and a
nonempty `comparisons` array. Each comparison needs `candidate_sha`,
`reference_version`, `reference_sha`, `campaign_url`, `environment`, and nonempty
`results`. Reference versions must be unique and exact, and SHAs must have 40
hexadecimal characters. Each reference gets a separate table on the release page.

Rows require `scenario`, `metric`, `unit`, `direction` (`lower` or `higher`),
`candidate`, `reference`, `delta_pct` (100 * (candidate/reference - 1)), `runs`,
`verdict`, `ci_method`, and `evidence_url`. Intervals `candidate_ci95`,
`reference_ci95`, and `delta_ci95` are two-number arrays or null with a
`ci_unavailable_reason`. Optional `disposition` records an exception separately
from the unchanged verdict. Evidence URLs must be permanent HTTPS links to
versioned campaign manifests, raw observations, and analysis.

No overall verdict is inferred from available rows. Missing coverage must be
explained in the linked campaign report. Unsupported/no-value measurements
remain in that report; do not invent numeric placeholders to satisfy the table.

`--check` detects stale generated HTML. Run the site tests to validate internal
links and reject incomplete evidence. Historical corrections must be versioned
and explained, keeping earlier campaign artifacts available.
