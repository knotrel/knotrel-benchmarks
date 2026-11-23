# Performance website

The static site is served directly from this directory, without Jekyll, Node,
external fonts or runtime dependencies. Existing methodology and research files
are preserved. The site uses Knotrel's mark and a distinct violet accent.

## Build and preview

```sh
python3 scripts/build_site.py
python3 scripts/build_site.py --check
python3 -m unittest discover -s scripts/tests -p 'test_build_site.py'
python3 -m pytest -q scripts/tests
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

Schema 1 rows require `scenario`, `metric`, `unit`, `direction` (`lower` or `higher`),
`candidate`, `reference`, `delta_pct` (100 * (candidate/reference - 1)), `runs`,
`verdict`, `ci_method`, and `evidence_url`. Intervals `candidate_ci95`,
`reference_ci95`, and `delta_ci95` are two-number arrays or null with a
`ci_unavailable_reason`. Optional `disposition` records an exception separately
from the unchanged verdict. Evidence URLs must be permanent HTTPS links to
versioned campaign manifests, raw observations, and analysis.

### Schema 2: verdict, category and execution status

Schema 2 adds outcomes that schema 1 cannot express. A dataset with
`schema_version: 2` may contain release entries with `schema_version: 2`. A
release entry without `schema_version` is a schema 1 entry and keeps exactly
the rules above, in a schema 1 or a schema 2 file, so no older entry is
rewritten. For display, a schema 1 row is read with the **documented
defaults** `category: decisive` and `status: completed`: schema 1 could only
express complete rows carrying a campaign verdict and every estimate. The
stored row is not changed.

Every row of a schema 2 entry carries three separate fields:

1. `verdict`: the analyzer's class, **exactly as measured**. Closed set:
   `PASS`, `PASS (IMPROVED)`, `FAIL`, `REGRESSION`, `INCONCLUSIVE`,
   `INCONCLUSIVE_DISCLOSED`, `UNRESOLVED`, `TIMER_LIMITED`, `EXCEEDS_BUDGET`,
   `INVALID`, `NOT_EQUIVALENT`, `NOT_RUN`, or JSON `null` (no verdict). No
   verdict is converted into PASS or merged into another; an analyzer
   qualifier such as `PASS (IMPROVED)` is kept as written. Any other value is
   rejected.
2. `category`: the row's role in the campaign's decision rule, independent of
   its verdict. Closed set:
   - `decisive`: enters the decision rule; a non-PASS verdict needs a
     recorded maintainer disposition;
   - `descriptive`: reported for context, outside the decision rule;
   - `disclosure`: reported by rule and never converted; does not block (for
     v1.0.0: C4 and the descriptive B4 frozen counterparts).
3. `status`: the execution status. Closed set, each admitting only these
   verdicts:

   | `status` | Meaning | Allowed `verdict` |
   | --- | --- | --- |
   | `completed` | Measured and analyzed | any measured class (not `NOT_RUN`, not null) |
   | `not_run` | Never measured (e.g. its experiment stopped after a product failure) | `NOT_RUN` |
   | `nonconforming` | Its block did not conform (e.g. a time cap): no verdict | `null` |
   | `failed` | Ran without an analyzable value (a product failure or an invalid observation) | `FAIL`, `INVALID` |

A row that is not `completed` requires a non-empty `status_reason` and
**carries no measured value**: `candidate`, `reference`, `delta_pct`, `runs`,
`candidate_ci95`, `reference_ci95` and `delta_ci95` must be absent or null.
`scenario`, `metric` and `evidence_url` stay required; `unit` and
`direction` are optional.

A `completed` row has every estimate under the schema 1 rules, except a
verdict that has no single estimate (a rule checked at every checkpoint or
observation, or a ratio whose reference is zero). Such a row carries a
non-empty `estimate_unavailable_reason` and no `delta_pct` or interval;
`candidate`, `reference` (finite, non-negative, with a `unit`) and `runs` are
optional. Rows whose reference column holds a threshold say so with
`reference_kind: "threshold"`.

Schema 2 intervals need not be 95 % intervals: `ci_method` states their
coverage, and the release page does not label them "95% CI".

The release page shows each verdict as a badge with its exact text, then the
category and status labels, and defines both. A row that is not `completed`
shows "No measurements" with its reason and no numbers, and gets no interval
plot. The badge colour only repeats what the text says, in both themes.

### Missing coverage

No overall verdict is inferred from available rows. Missing coverage must be
explained in the linked campaign report. Unsupported/no-value measurements
are published as schema 2 rows with their reason; do not invent numeric
placeholders to satisfy the table.

`--check` detects stale generated HTML. Run the site tests to validate internal
links and reject incomplete evidence. Historical corrections must be versioned
and explained, keeping earlier campaign artifacts available.
