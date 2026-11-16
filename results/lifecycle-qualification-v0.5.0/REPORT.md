# Knotrel v0.5.0 performance qualification report (M10)

**Final candidate measured:** knotrel `649425373a510a3a18c25519d21c5cf8b43e13fe`
(branch `feature/v0.5.0-node-edge-lifecycle`). **Outcome: NOT PASSED
unconditionally.** Experiment A has 3 UNRESOLVED cells; B has 9 REGRESSIONs and
1 INCONCLUSIVE; C has 18 heap-growth FAILs. None is waived. They need owner
decisions (section 5).

Protocol: knotrel-benchmarks `results/lifecycle-qualification-v0.5.0/PROTOCOL.md`
(frozen at `450ba04a`, amendment 1 at `3942762a`). Host: Apple M3, macOS 26.5.2,
rustc 1.100.0, AC power. Results apply only to these workloads and this host.

## 1. Runs

| Run | Candidate | A | B/C | Status |
|---|---|---|---|---|
| 1 | `ea12706` | `A-20261116T001606Z-ea12706/` | `BC-final-ea12706/` | preserved; see `RUN-1-ea12706.md` |
| 2 | `6494253` | `A-20261116T011844Z-6494253/` | `BC-final-6494253/` | **final** |

Run 1 found 31 B REGRESSIONs. Diagnosis traced most of them to two facade
defects (identity-hashed catalog; ascending cut order), fixed in `6494253`.
Run 2 repeated every experiment with the same matrix, rules, thresholds and
seeds; only the candidate and the mechanically re-derived window sizes
changed (amendment 1). Measured runtime in total: about 1 h 45 min (four
pilots ~10 min, run 1 ~42 min, run 2 ~55 min), within the 6 h cap.

Validation of each run: every cell present with exit 0, AC power, frozen
window multipliers, every probe build record naming the clean candidate and
tooling revision, balanced order, 2 warmup + 12 pairs, digest and end-state
verification (core) and connectivity agreement (HTTP).

## 2. Experiment A: existing behavior against v0.4.0 (lifecycle disabled)

v0.4.0 design and rules unchanged (`final-decision-analysis.json`); medians in
ns (time to ready in ms). The v0.4.0 waivers do not carry forward.

| Cell | Pairs | Primary median v0.4.0 → candidate | Primary change [interval] | Non-PASS supporting metrics | Outcome |
|---|---|---|---|---|---|
| `core_sparse_traversal_10k_compact-bfs_warmed` | 12 | 4.651e+06 → 4.633e+06 | -0.73% [-11.31, +4.35] | — | **PASS** |
| `core_sparse_traversal_10k_compact-workspace_warmed` | 24 | 5.073e+06 → 5.45e+06 | +7.94% [+2.16, +11.31] | — | **INCONCLUSIVE_DISCLOSED** |
| `core_sustained_churn_10k_compact-bfs_warmed` | 12 | 6.726e+05 → 6.713e+05 | -0.14% [-0.61, +0.52] | — | **PASS** |
| `core_sustained_churn_10k_compact-workspace_warmed` | 12 | 4.754e+05 → 4.749e+05 | -0.10% [-1.31, +0.46] | — | **PASS** |
| `http_lifecycle_compact_bfs_small` | 24 | 4.863 → 4.957 | -1.93% [-15.62, +23.91] | — | **INCONCLUSIVE_DISCLOSED** |
| `http_standalone_batch_b1_compact_bfs` | 24 | 1.651e+08 → 1.692e+08 | +4.23% [-4.46, +8.81] | request_latency_p99_ns INCONCLUSIVE +17.04% [-27.31, +68.98] | **UNRESOLVED** |
| `http_standalone_batch_b256_compact_bfs` | 24 | 2.952e+06 → 2.985e+06 | -0.80% [-3.75, +3.19] | sampled_max_rss_bytes INCONCLUSIVE +0.65% [-2.32, +21.01] | **UNRESOLVED** |
| `http_standalone_batch_b64_compact_bfs` | 24 | 7.168e+06 → 6.824e+06 | -1.87% [-11.94, +3.42] | sampled_max_rss_bytes INCONCLUSIVE +2.80% [-1.62, +22.13] | **UNRESOLVED** |
| `http_standalone_batch_b8_compact_bfs` | 24 | 2.818e+07 → 2.893e+07 | -0.10% [-8.60, +4.91] | — | **PASS** |

Summary: 4 PASS, 2 INCONCLUSIVE_DISCLOSED, **3 UNRESOLVED**, no REGRESSION.
Batch-1 request p99 was UNRESOLVED in v0.4.0 and in run 1 as well. The b64 and
b256 RSS intervals exceed the 20% tolerance only in their upper bound (22.1%,
21.0%), with medians +2.80% and +0.65%. Not covered by A: ETT/HDT, feeder,
import and metrics-enabled operation (see B).

## 3. Experiment B: lifecycle cost (run 2)

| Group | PASS | REGRESSION | INCONCLUSIVE | Run 1 for comparison |
|---|---|---|---|---|
| B1 lifecycle operations vs application-side reference (60) | 60 | 0 | 0 | 54 / 5 / 1 |
| B2 opt-in cost on legacy operations (27, t = 50%) | 27 | 0 | 0 | 27 / 0 / 0 |
| B3 degree effects (24) | 21 | 3 | 0 | 6 / 18 / 0 |
| B4 opt-in HTTP (12) | 12 | 0 | 0 | 12 / 0 / 0 |
| B4 lifecycle ops and query HTTP (14) | 14 | 0 | 0 | 11 / 3 / 0 |
| B4 feeder events (7) | 7 | 0 | 0 | 6 / 0 / 1 |
| B4 imports (17, t = 100%) | 11 | 6 | 0 | 12 / 5 / 0 |
| B4 metrics on vs off (6, t = 6%) | 5 | 0 | 1 | 5 / 0 / 1 |

Non-PASS cells (reference → candidate median window):

| Cell | Reference | Candidate | Change [interval] | t | Status |
|---|---|---|---|---|---|
| B3 degree-remove ETT 16,384 | 28.29 ms | 36.45 ms | +29.07% [+27.61, +30.64] | 25% | REGRESSION |
| B3 degree-remove HDT 16,384 | 36.23 ms | 59.21 ms | +63.52% [+62.43, +67.91] | 25% | REGRESSION |
| B3 degree-remove HDT 4,096 | 8.36 ms | 11.90 ms | +41.61% [+40.78, +43.64] | 25% | REGRESSION |
| B4 import compact-bfs hub 10k | 2.25 ms | 4.60 ms | +104.57% [+102.85, +107.70] | 100% | REGRESSION |
| B4 import compact-bfs sparse 10k | 2.46 ms | 5.84 ms | +136.84% [+132.79, +148.19] | 100% | REGRESSION |
| B4 import compact-bfs sparse 100k | 13.23 ms | 36.51 ms | +168.45% [+166.60, +177.47] | 100% | REGRESSION |
| B4 import 60% inactive compact-bfs 10k | 2.88 ms | 20.81 ms | +620.09% [+608.72, +628.87] | 100% | REGRESSION |
| B4 import 60% inactive ETT 10k | 2.95 ms | 12.31 ms | +316.55% [+308.96, +338.29] | 100% | REGRESSION |
| B4 import 60% inactive HDT 10k | 3.47 ms | 12.66 ms | +265.35% [+254.09, +271.63] | 100% | REGRESSION |
| B4 metrics-ops compact-bfs 10k | 2.89 ms | 3.01 ms | +6.00% [+0.64, +9.37] | 6% | INCONCLUSIVE |

Interpretation, without changing any verdict:
- **Imports:** the reference imports only the effective graph and keeps the
  flags in a lean application store, so it parses and builds fewer edges
  (about 11% of them at 60% inactive). Flagged imports carry and build the
  full registered topology. At 20% inactive, flagged imports passed on ETT
  and HDT (where the engine build dominates) and failed on compact-bfs. The all-active
  legacy import on a lifecycle server (`import-optin`) passed in every cell.
- **High-degree removal on ETT/HDT** remains 1.3x-1.6x the unordered
  reference at degree >= 4,096 after the ordering fix (run 1: up to 39x).
  Default-engine removal is faster than the reference (up to -84%).
- Lifecycle operations (B1), lifecycle HTTP batches and feeder events now
  pass against the equivalent application code. Opt-in cost on legacy
  operations passed everywhere, the largest being ETT (+30.6% at hub 100k).

The full per-cell table is `BC-final-6494253/analysis.md`.

## 4. B5 memory and C sustained resources

B5 net live heap after building 100k nodes, lifecycle / plain: compact-bfs
2.45x (sparse), 2.44x (hub); ETT 1.24x; HDT 1.16x. All within the 3.0x budget.

C (lifecycle arm, 30 cycles of 5% churn):
- **C1 engine slots: PASS in all 90 lifecycle cells.** The maximum number of
  retired slots stayed within the 2V + 1024 bound (for example 95,000 at
  100k-node fresh churn).
- **C2 logical counts: PASS in all 180 cells** (both arms) against the
  independent model.
- **C3 heap growth: 27 PASS, 18 FAIL.** The failures are HDT same-ID and toggle
  churn at every size (for example 99.1 → 252.4 MiB at 100k; the reference arm
  grows equally, 103.0 → 258.7 MiB), ETT same-ID and toggle churn on ring and
  hub 100k, and fresh-ID churn at 100k on compact-bfs and ETT ring (within
  the documented slot bound, above the 1.25x / 10% rule). Same-ID and toggle
  growth appears equally in the reference arm: it is engine growth under
  sustained churn, not catalog growth (catalog and incident capacities stay
  flat).
- **C4 RSS: 16 PASS, 29 EXCEEDS_BUDGET** (disclosure; allocator retention).

## 5. Decisions needed from the owner

1. **A UNRESOLVED (3 cells):** batch-1 request p99, and b64/b256 sampled RSS.
2. **B3 REGRESSION (3 cells):** high-degree `remove_node` on ETT/HDT is
   1.3x-1.6x the application-side reference.
3. **B4 import REGRESSION (6 cells):** flagged imports exceed the 2x budget
   against a reference that imports only the effective graph.
4. **B4 metrics INCONCLUSIVE (1 cell):** metrics-on lifecycle batches at the
   6% budget boundary.
5. **C3 FAIL (18 cells):** engine heap growth under sustained churn, shared
   with the reference arm; and fresh-ID growth within the slot bound.

No claim is made beyond the measured workloads and host.
