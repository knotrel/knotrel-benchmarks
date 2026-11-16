# v0.5.0 maintainer decision on qualification results (recorded 2026-11-16)

Recorded as stated by the maintainer in the session; quoted scope, not
paraphrased into a broader acceptance.

**Candidate:** knotrel `dcd8ccca10ef5766e3c9252832594186bf93bbc3`, node and edge
lifecycle limited to `compact-bfs` (owner decision B1). Evidence: run 4
(`RUN-4-dcd8ccc.md`, `A-20261116T113709Z-dcd8ccc/RESULT.md`,
`BC-final-dcd8ccc/analysis.json`, `D5/`), disposition package
`MAINTAINER-DISPOSITION-dcd8ccc.md`.

## Explicitly accepted, for v0.5.0 only

These are maintainer waivers made **after** the results. They do not change
any threshold or verdict, do not demonstrate the absence of a regression, and
do not carry over automatically to future releases.

1. Experiment A, UNRESOLVED:
   - HTTP batch 1, request p99: 119.4 → 132.6 µs; +6.04% [−27.84%, +50.04%]
     against 25%.
   - HTTP batch 64, sampled max RSS: 6.94 → 7.03 MB; +0.11% [−3.50%, +25.14%]
     against 20%.
2. Import REGRESSIONs (lifecycle enabled):
   - 100k nodes: 14.12 → 29.41 ms per import; +109.9% [+101.9%, +115.9%]
     against 100%.
   - 60% inactive / 30% disabled, 10k nodes: 0.43 → 2.35 ms per import;
     +444.8% [+427.3%, +464.6%] against 100%.
3. C3 heap-growth FAILs under fresh-ID churn (sparse, ring, hub; 100k nodes).
4. B4 INCONCLUSIVE cells, including the uncertainty whether each meets its
   budget:
   - import 10k: 1.30 → 2.59 ms per import; +100.8% [+96.1%, +107.0%] against
     100%;
   - `metrics-ops` (lifecycle on, metrics on vs off): 70.5 → 75.3 µs per
     request; +6.5% [+5.3%, +8.3%] against 6%;
   - `metrics-legacy` on ETT (lifecycle off, metrics on vs off): 277.5 →
     288.3 µs per request; +4.0% [+1.0%, +6.4%] against 6%.

## Acknowledged

- The HTTP startup INCONCLUSIVE_DISCLOSED cell, under the existing policy.
- The observed import and compaction peaks (observations, not ceilings).
- The C4 RSS disclosures and the absence of a guaranteed RSS bound.

## Not covered by this decision

Publication approval. CI on the release commit, the release dry run,
packaging and publication checks, the signed tag and any push, merge or
publication remain separate gates. The cause of the single
`test_regression_early_exit_with_diagnostics` failure remains not established.
