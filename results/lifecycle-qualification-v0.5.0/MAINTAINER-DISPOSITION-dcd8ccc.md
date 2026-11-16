# v0.5.0 maintainer-disposition package — candidate dcd8ccc

Sources: `A-20261116T113709Z-dcd8ccc/final-decision-analysis.json`,
`BC-final-dcd8ccc/analysis.json`, `D5/`, `D4/`, `RUN-4-dcd8ccc.md`. Every verdict
below is the original one; nothing is relabeled. Medians are per paired
window; "ref" is v0.4.0 (experiment A) or the semantically equivalent
reference (experiment B); "cand" is dcd8ccc.

## 1. Decision table

### Legacy / default behavior (lifecycle disabled; affects every user)

| # | Cell / metric | Ref → cand (medians) | Paired change [interval] | Threshold | Verdict | Practical impact | Possible explicit waiver scope |
|---|---|---|---|---|---|---|---|
| 1 | A `http_standalone_batch_b1_compact_bfs`, request p99 | 119.4 → 132.6 µs | +6.04% [−27.84, +50.04] (24 pairs) | 25% | INCONCLUSIVE → cell **UNRESOLVED** (primary window +0.04% [−5.57, +5.32] PASS) | Tail latency of single-operation requests; median within tolerance, interval cannot exclude −28% to +50%. Unresolved also for 6494253 and a1d9577 | Batch-1 request p99, default compact-bfs config, dcd8ccc only |
| 2 | A `http_standalone_batch_b64_compact_bfs`, sampled max RSS | 6.94 → 7.03 MB | +0.11% [−3.50, +25.14] | 20% | INCONCLUSIVE → cell **UNRESOLVED** (window −2.11% PASS, p99 PASS) | Equal medians; RSS samples are bimodal (~5.5 vs ~7.1 MB) in both arms; the interval's upper end is about +1.7 MB of process RSS | Batch-64 sampled RSS, dcd8ccc only |
| 3 | A `http_lifecycle_compact_bfs_small` (lifecycle = source-managed startup, not M10), time to ready | 4.72 → 4.81 ms | +5.14% [−17.35, +22.13] | 10% | **INCONCLUSIVE_DISCLOSED** (allowed by v0.4.0 rules; supporting metrics PASS) | About +0.1 ms median startup | Disclosure acknowledgment only |
| 8 | B4 `metrics-legacy-ett-sparse-10000` (metrics on vs off, **lifecycle disabled**, experimental ETT) | 277.5 → 288.3 µs per request | +4.0% [+1.0, +6.4] | 6% | **INCONCLUSIVE** (PASS in run 3: +2.5%; compact-bfs +1.6% and hdt +2.8% PASS) | Metrics overhead on ETT servers, up to about 18 µs per request at the upper bound; not lifecycle and not a v0.4.0→v0.5.0 comparison | Metrics overhead, ETT, lifecycle off |

### Lifecycle-enabled costs (opt-in, compact-bfs only)

| # | Cell / metric | Ref → cand | Paired change [interval] | Threshold | Verdict | Practical impact | Possible explicit waiver scope |
|---|---|---|---|---|---|---|---|
| 4 | B4 `import-compact-bfs-sparse-100000`, import window | 14.12 → 29.41 ms per import | +109.9% [+101.9, +115.9] | 100% | **REGRESSION** | About +15 ms per 100k-node bootstrap or replacement import (one-off per import). Reference lacks incident index, validation and atomic publication (favors the reference) | Flagged import, lifecycle on, ≤100k nodes |
| 5 | B4 `import-high-compact-bfs-sparse-10000` (60% inactive, 30% disabled) | 0.43 → 2.35 ms per import | +444.8% [+427.3, +464.6] | 100% | **REGRESSION** | About +1.9 ms per 10k-node import; parsing the contract's non-effective entries alone exceeds the budget (amendment 2) | Flag-heavy imports, lifecycle on |
| 6 | B4 `import-compact-bfs-sparse-10000` | 1.30 → 2.59 ms per import | +100.8% [+96.1, +107.0] | 100% | **INCONCLUSIVE** | About +1.3 ms per 10k-node import | Same family as 4 |
| 7 | B4 `metrics-ops-compact-bfs-sparse-10000` (lifecycle + metrics on vs off) | 70.5 → 75.3 µs per request | +6.5% [+5.3, +8.3] | 6% (pre-approved v0.4.0 metrics budget) | **INCONCLUSIVE** (median above budget, lower bound below) | About +5 µs per lifecycle batch request with metrics enabled | Metrics overhead, lifecycle on |

### Memory and resources (lifecycle on, compact-bfs, 100k nodes)

| # | Item | Values | Threshold | Verdict | Practical impact | Possible waiver scope |
|---|---|---|---|---|---|---|
| 9 | C3 heap, fresh-ID churn: sparse / ring / hub | heap 23.0→34.5 (max 37.3), 19.4→31.8 (33.1), 22.5→34.2 (36.9) MiB; late/early 0.97 / 1.01 / 0.97 (≤ 1.25 PASS); projected 30-cycle slope +0.117 / +0.208 / +0.136 | slope ≤ 0.10 | **3 FAIL** (C1 slots and C2 counts PASS; same-ID and toggle PASS) | Heap rises with retired slots and falls at compaction (cycle 20): sawtooth | Fresh-ID churn heap growth within the compaction policy |
| 10 | Peaks (D5 diagnostic, no gate) | compaction peak 49.2 MiB net vs 37.3 steady max (+11.9); HTTP import peak 111.2 / 128.6 MiB (create 20/10, 60/30) and 130.3 MiB (replace) for ~24 MiB final graph; core import peak +1.3 to +2.8 MiB | none | disclosure | Memory sizing must cover transient peaks ~1.3× steady (compaction) and ~4.6-5.4× the final graph during HTTP import; plain-import peak not measured | Documented sizing guidance |
| 11 | C4 RSS (disclosure-only by protocol) | 8 of 15 cells EXCEEDS_BUDGET; RSS net growth up to 26.1 MiB (ring fresh); 66-103 MiB RSS at cycle 30 (D5) | slope/late-early disclosure budget | **EXCEEDS_BUDGET** (disclosure) | RSS has no hard bound (allocator retention) | Disclosure |

## 2. Provenance around the stale Cargo cache

- **Affected step:** validation `python-tests`, test class
  `test_release_publishing.TestMedium7VerifySourcePackages`, which runs
  `scripts/verify-source-packages.sh` in the worktree. Its `cargo package`
  verification of `knotrel-server` resolved `knotrel-core 0.5.0` through a
  temporary registry with a path-derived ID and reused (a) a 00:35 source
  extraction in `~/.cargo/registry/src/-eb5daf03efd0fd38/` and (b) a compiled
  registry `knotrel-core` in the worktree `target/`.
- **Correction:** (a) moved aside (not deleted); (b) `cargo clean` of the
  worktree target; attempt 3 passed 47/47 at 12:36:47 local. The separate
  `source-packages` step (fresh clone, own target) passed in the first run.
- **Measured binaries unaffected (evidence):**
  - built 12:38:08-12:39:04 local, after the correction, in new target
    directories (A `targets/`, probes `target-r4*`) never shared with the
    worktree's target;
  - `knotrel-core` is a **path** dependency in all three lockfiles used (A
    harness, A server workspace, probes: no `source` entry), so the registry
    cache cannot supply it; A build logs show `Compiling knotrel-core v0.5.0
    (…/sources/C/knotrel/crates/knotrel-core)` and the harness path through the
    `build-inputs/C/knotrel → sources/C/knotrel` symlink (checkout `dcd8ccc`,
    clean);
  - probe build records: knotrel `dcd8ccc` clean, probes `f1d099cc` clean;
    provenance hashes equal amendment 4's table; A identities equal amendment
    4's table;
  - the measured candidate binaries contain B1-only code: A C server and probe
    `http-lifecycle` contain both new error texts; all probe binaries contain
    `UnsupportedEngine`; the v0.4.0 B server contains neither.
- **Earlier validations:** their python-tests package verification may have
  compiled `knotrel-server` against an older core extraction; that step is
  weaker evidence for earlier candidates. Not relevant to dcd8ccc.

Conclusion: no contamination of measured artifacts; verified, not inferred.

## 3. Memory evidence scope

- **Reclamation policy:** a removed node leaves a retired engine slot (reused
  for the same ID); after every removal, when retired slots exceed
  `max(registered nodes, 1024)`, the engine is rebuilt from the catalog. Hence
  engine vertices ≤ 2 × registered nodes + 1024 at every operation boundary
  (C1 PASS; max 195,000 ≤ 201,024). Fresh-ID churn adds a retired slot per
  removal until the rebuild: the heap sawtooth is this policy working as
  designed, not unreclaimed storage. D4b observed the same bounded sawtooth
  over 120 cycles.
- **What the slot bound does not cover:** total heap (catalog hash-table
  capacity, which doubled once under fresh-ID churn; vector capacities), the
  temporary reconstruction peak (old + new engine + order/effective vectors),
  HTTP import transients, and RSS (allocator retention).
- **No ceiling claimed:** observed maxima (37.3 MiB steady, 49.2 MiB peak,
  130 MiB import peak) are single observations on this host and schedule,
  not guarantees.

## 4. Test uncertainty

- `test_external_server_engine_mismatch_rejection`: AddrInUse port race
  confirmed (captured stderr) and fixed in the harness (`754ddbc`); 20 post-fix
  runs passed. Residual: another `free_address()` use (Python mock test) has the
  same theoretical race, not observed.
- `test_regression_early_exit_with_diagnostics`: failed once (6494253 clone,
  first of 40 reproduction runs, cold start that also built the test example;
  elapsed 1.59 s against a 1.5 s assertion). Passed in 59 later recorded
  reproduction runs and in dcd8ccc validation (default and all-features).
  **Cause not established**; it is a wall-clock assertion and may fail under
  load. Not resolved, not shown to be pre-existing. Whether it affects
  required CI is unknown until CI runs.

## 5. Recommendations (item by item)

| # | Item | Recommendation |
|---|---|---|
| 1 | A batch-1 request p99 UNRESOLVED | Explicit owner decision: accept with disclosure |
| 2 | A batch-64 RSS UNRESOLVED | Explicit owner decision: accept with disclosure |
| 3 | A startup INCONCLUSIVE_DISCLOSED | Acknowledge disclosure |
| 4 | Import 100k REGRESSION | Explicit waiver with disclosure |
| 5 | Import 60/30 REGRESSION | Explicit waiver with disclosure; budget specification to be revisited in a later protocol (no change now) |
| 6 | Import 10k INCONCLUSIVE | Accept with disclosure |
| 7 | metrics-ops INCONCLUSIVE | Accept with disclosure |
| 8 | metrics-legacy ETT INCONCLUSIVE | Accept with disclosure (non-lifecycle, experimental engine) |
| 9 | C3 fresh-ID FAILs (3) | Explicit waiver with disclosure |
| 10 | Compaction/import peaks | Accept with disclosure; keep deployment sizing guidance |
| 11 | C4 RSS | Accept with disclosure (no RSS bound) |
| — | Artifact provenance | Verified; no further action |
| — | `test_regression_early_exit_with_diagnostics` | Further verification through required CI; hold release only if it fails there |

No item requires holding the release on current evidence, and no new broad
investigation is recommended.

## Proposed maintainer decision

For v0.5.0 candidate `dcd8ccc` (lifecycle on `compact-bfs` only), the
maintainer explicitly accepts, with the disclosures above and without changing
thresholds or verdicts: (a) the two UNRESOLVED experiment-A metrics (batch-1
request p99; batch-64 sampled RSS); (b) the two flagged-import REGRESSIONs
(100k nodes +109.9%; 60/30 flags +444.8%); (c) the three fresh-ID C3 heap-growth
FAILs; and acknowledges the INCONCLUSIVE_DISCLOSED startup cell, the three B4
INCONCLUSIVE cells, the documented compaction and import peaks, the C4 RSS
disclosures and the absence of an RSS bound. These decisions apply to dcd8ccc
only and set no precedent.

## Remaining checks before release

1. Confirm the release commit's executed code equals `dcd8ccc` (protocol §8;
   current head `d4e5935` adds documentation only).
2. CI on the release commit, including the test suite (watch
   `test_regression_early_exit_with_diagnostics`), and the release dry run.
3. Source-package verification and publication checks on the release commit
   (fresh environment, no stale Cargo cache).
4. Maintainer approval, signed tag, then push/merge and publication (each
   requires explicit authorization).
