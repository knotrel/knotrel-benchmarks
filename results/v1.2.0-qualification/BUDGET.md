# v1.2.0 release qualification: budget (knotrel#182)

Recorded before any frozen collection, as the plan (knotrel
`docs/releases/v1.2.0-qualification-plan.md`, sections 8 and 11) requires.

**Cap: 5.0 host hours for the single session** (`rules.cap_hours` in `v120q-matrix.json`).
There is no second session (`second_session_cap_hours` = 0). When the cap is reached, the
cells not yet complete are reported `INCOMPLETE`, never classified.

## Derivation from the preparatory duration trial

The trial ran on 2026-11-27 from 08:27:52 to 09:36:03 UTC+1 (68 min) against the
pre-freeze candidate 9faf168 and tooling 6b47a04. It used `run_cf5.py --preparatory --pairs 2
--warmup 0 --no-smoke`, with no swap activity. Its results decide nothing.

| Block | Trial | Frozen run | Basis |
|---|---|---|---|
| V1 (delegated) | 27 min | 27 min | full frozen plan (108 pairs) in the trial |
| Q (delegated) | 29 min | 45 min | worst case: the Q cap is 2700 s |
| B4 (delegated) | 2 min | 2 min | full `final` profile in the trial |
| V2 | 109 s, 2 pairs | 24 min | × 13 (26 pairs incl. 2 warmup) |
| K2 | 504 s, 2 pairs | 109 min | × 13 |
| K1 | 26 s, 2 pairs | 6 min | × 13 |
| Smoke and setup | not run | 5 min | allowance |
| **Total** | 68 min | **218 min (3.6 h)** | |

With a 30 % margin: 4.7 h, rounded up to a 5.0 h cap.
