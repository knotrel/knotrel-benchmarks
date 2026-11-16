# Experiment A on candidate a1d9577 (amendment 3, rerun after environmental invalidation)

Attempt 1 (08:35-08:42Z) was invalidated by the collector (host on battery) and
is preserved in `raw-main-attempt1-invalid/`; it is not used. The single
permitted rerun: main 2026-11-16T09:23:07Z-09:36:33Z (108 pairs), extension
09:36:33Z-09:49:51Z (48 pairs, 4 cells), both exit 0, AC power at every session
check. Pre-launch checks: every binary, lockfile, plan and schedule hash equal
to `identities.json` and amendment 3; no build running. The agent ran no other
command during the collection. Analysis: `final-decision-analysis.json`
(`--rules v0.4.0`), exit 0.

| Cell | Outcome | Primary (pairs) | Note |
|---|---|---|---|
| core sparse traversal compact-bfs | **UNRESOLVED** | +4.92% [−2.35, +23.52] (24) | `connected_p99_ns` INCONCLUSIVE +4.64% [−0.43, +26.54] |
| core sparse traversal compact-workspace | PASS | −9.80% [−18.12, −2.12] (12) | |
| core sustained churn compact-bfs | PASS | +1.06% [−0.89, +4.04] (12) | |
| core sustained churn compact-workspace | PASS | +1.06% [−0.94, +3.59] (12) | |
| HTTP lifecycle startup | INCONCLUSIVE_DISCLOSED | +2.44% [−28.98, +17.78] (24) | |
| HTTP batch 1 | **UNRESOLVED** | +2.73% [−3.27, +5.42] PASS (24) | request p99 INCONCLUSIVE +3.79% [−18.82, +63.70] |
| HTTP batch 8 | PASS | −0.55% [−14.95, +6.61] (12) | |
| HTTP batch 64 | **UNRESOLVED** | −0.15% [−3.25, +2.63] PASS (24) | sampled max RSS INCONCLUSIVE +1.18% [+0.58, +21.64] (t = 20%) |
| HTTP batch 256 | PASS | −1.21% [−6.37, +2.39] (12) | |

Summary for `a1d9577`: 5 PASS, 1 INCONCLUSIVE_DISCLOSED, 3 UNRESOLVED, no
REGRESSION. Run 2's result for `6494253` (4 PASS, 2 INCONCLUSIVE_DISCLOSED,
3 UNRESOLVED) remains that candidate's record; neither replaces the other. With
unchanged executed source paths, two cells changed classification between the
candidates (compact-bfs sparse traversal PASS → UNRESOLVED; compact-workspace
sparse traversal INCONCLUSIVE_DISCLOSED → PASS), consistent with the documented
layout and run-to-run sensitivity; no claim of improvement or regression is
made from that difference.
