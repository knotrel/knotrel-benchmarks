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
manually transcribing measurements. The site contains the published 1.0.0
report (qualification **accepted with exceptions**, exported by
`scripts/export_v100q_site.py`) and no fabricated values or verdicts. 1.0.0
remains the latest published release until the 1.1.0 tag; a 1.1.0 entry is
added only from its own release comparison.

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

A published schema 2 release entry also states which exact release it
describes and the maintainer's release-level decision, so a report on a
release candidate is never read as a stable release or as "all gates PASS":

- `release_label`: the exact release, for example `1.0.0-rc.1` for the `1.0.0`
  entry; its `X.Y.Z` must equal `version`. A label with a prerelease suffix is
  shown as a prerelease (release candidate), never as a stable release.
- `qualification_decision`: `accepted`, `accepted with exceptions` or
  `not accepted`, as written in the decision record. It never changes a row
  verdict.
- `decision_url`: the permanent HTTPS URL of the decision record.
- `qualification_note` (optional): nonempty text shown with the decision, for
  example when a qualification measured on a candidate is transferred to the
  release under a recorded waiver.

The exporter sets `release_label` from the freeze record's candidate version and
takes the other two from `--qualification-decision` and `--decision-url`.
For 1.0.0 the exporter's label (`1.0.0-rc.1`, the measured candidate's
version) was changed by hand to `1.0.0`, with a `qualification_note`, when the
maintainer released 1.0.0 directly and transferred the qualification under a
waiver (2026-11-24, `results/v1.0.0-qualification/DECISION.md` section 6). No
measurement or verdict was changed.

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

## Engine comparisons

`docs/data/engine-comparisons.json` holds comparisons of engines on **one
build**, which the release schema cannot express (it compares a candidate with
earlier releases). The generator renders `engines.html` and one
`engines/<id>.html` page per entry; the page title and eyebrow say that it is
an engine comparison on one build, not a release comparison.

The first entry, `cluster-forest-cf5-02cba68`, is the v1.1.0 CF5
qualification (`results/v1.1.0-cf5/REPORT.md`). Regenerate it from the
analyzers' outputs, never by hand:

```sh
python3 scripts/export_cf5_site.py --report-url <commit permalink of REPORT.md> \
  --evidence-url <commit permalink of analysis/attempt1>
python3 scripts/build_site.py
```

Schema 1 (`schema_version: 1`), checked by `validate_engines`:

- identity: a slug `id`, `title`, `kind`, `candidate_engine`,
  `reference_engines`, 40-character `candidate_sha` and `tooling_sha`,
  `campaign`, `environment`, `method` and the maintainer's `decision`;
- `report_url` and `evidence_url` must be **commit permalinks**
  (`https://github.com/<owner>/<repo>/blob|tree/<40-hex SHA>/...`), so the page
  never follows a moving branch;
- `limitations`: nonempty; the first is shown at the top of the page and on
  the index card (for CF5, the host swap limitation of decision D1);
- `families`: per workload family, the analyzer's statement against each
  reference, from the closed set of plan section 12 (`prefer cluster-forest`,
  `prefer reference`, `mixed results`, `insufficient evidence`,
  `no difference beyond the margins`, `isolated differences`), the classes of
  every metric of the family's cells (`FASTER`, `SLOWER`, `EQUIVALENT`,
  `INCONCLUSIVE`, `TIMER_LIMITED`, `SMALLER`, `LARGER`, `SIMILAR`) and the range
  of their median paired ratio (timed metrics, three significant figures; below
  1 favours the candidate engine);
- `block_counts`: every metric class per block and reference;
- `lifecycle_rules`: C1–C4 counts and **every** C3 FAIL and C4
  EXCEEDS_BUDGET run with the analyzer's numbers. A C3 FAIL requires
  `lifecycle_disposition`; the projected 30-cycle growth is labelled as a
  projection from the slope, never as measured growth.

No class or statement is converted, merged or dropped.

