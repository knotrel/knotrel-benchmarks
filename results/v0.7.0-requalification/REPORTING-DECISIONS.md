# v0.7.0 re-qualification: maintainer decisions after the freeze

Decisions taken after FREEZE-A3 revision 2 that affect the analysis or the
report. Earlier decisions are recorded in MATRIX.json (`amendment_1`–
`amendment_3`) and the FREEZE records. None of these decisions disposes of a
result.

| Date | Question put to the maintainer | Answer |
|---|---|---|
| 2026-11-18 | After a3-2 FAILED at B/C: fix the launch environment and refreeze? | "Fix and refreeze" (FREEZE-A3 revision 2) |
| 2026-11-18 | Prepare a3-3, the last attempt? | "Yes, prepare a3-3" |
| 2026-11-19 | Write the comparison report, with per-cell conformance taken from the gate records (the first campaign's `analyze_v070_conformance.py` cannot read the re-qualification monitor)? | "Yes, write report" |

| 2026-11-19 | §9 item 1, B4 `import-high` REGRESSION | "Diagnostic first. Update the cost breakdown and add a capability-equivalent comparison. The existing evidence does not establish that the entire overhead is unavoidable. Preserve the original verdict and thresholds; no acceptance yet." |
| 2026-11-19 | §9 item 2, C3 heap growth FAIL ×3 | "Verify that growth remains bounded over repeated compaction cycles and evaluate mitigation costs, including pre-sizing. Report peak memory and steady-state behavior. Preserve the FAIL results; no acceptance yet." |
| 2026-11-19 | §9 item 3, B4 `ops` sparse 100k INCONCLUSIVE | "Profile lifecycle batch overhead at 100k and identify actionable costs. Any additional measurement must remain separate from the existing INCONCLUSIVE result." |
| 2026-11-19 | §9 item 4, B4 `metrics-ops` sparse 10k INCONCLUSIVE | "Isolate metrics recording and lock-timing overhead. Identify whether the 6% budget can be met without reducing observability. Preserve the existing INCONCLUSIVE result." |
| 2026-11-19 | Release and §9 item 6, M_desc 412 | "Keep the release pending these investigations. Also diagnose the 6/6 replacement imports rejected with HTTP 412 at 64 clients, distinguishing expected precondition enforcement, probe error and product defect. Do not change thresholds or accept exceptions without my explicit decision." |

**State after these decisions.** The release is pending. Items 1–4 and 6
have diagnostics ordered; their verdicts (REGRESSION, FAIL, INCONCLUSIVE,
INVALID) stand unchanged and no threshold changes. Diagnostics are separate
collections (`DIAGNOSTICS-PLAN.md`): they add evidence for the maintainer and
never replace a result of attempt a3-3. Items 5 and 7–10 have no decision yet.
