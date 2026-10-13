# ETT scan-root manual-counter campaign on Apple M4 — 2026-10-12

This is a new 72-process marker-scoped campaign. It reuses the prior frozen
seed-1012 plan unchanged (`SHA-256 585c4071526d3113210c94953d6175e0040140f04112c238b413b7a505200ae5`)
after the separate mapping experiment demonstrated the `counters-profile`
array mapping and exact duplicate group.

The user-provided manual template is read-only at
`$HOME/Downloads/MyTemplate.tracetemplate`, SHA-256
`99b0cb00c8c35bdd66fb6456021ea11c21c0c3e36c89b0b4e5975ea5622ecd74`.
For each sample, positions 0–7 are the configured events and positions 8–15
must be their exact duplicate. The raw trace bundles and bulky counter exports
are stored outside Git under the session artifact root recorded per batch.

The final [engineering report](report.md) retains the 36 paired duration
comparisons, confidence intervals, individual regressions, counter coverage,
and the boundary between descriptive counter observations and reliable metrics.
The related [implementation assessment](implementation-assessment.md) explains
why captured scan-root reuse is effective for dense replacement scans but is
not exercised by the no-candidate path workload.
The focused [correctness review](correctness-review.md) records the
component-root invariant, replacement/mutation lifecycle review, and tests run
against the isolated profiled candidate.
