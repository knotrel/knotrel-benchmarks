# D2c: catalog tombstone handling (item 3, phase 3)

This diagnostic follows DIAGNOSTICS-PLAN-3.md, D2c. It is not part of the
qualification. The a3-3 C3 FAILs stand.

**Setup.**
- **Build:** a diagnostic build of candidate e75ff6a (`d2c-core.diff`; probe
  changes in `d2c-probe.diff`), with the policy selected by `KNOTREL_D2C`:
  - frozen: unchanged;
  - **T1:** before an insert that would grow the catalog table, rebuild it at
    the same size when live entries are at most 90% of its full capacity;
  - **T2:** T1, plus the same rebuild after each engine compaction.
- **Count build.** The allocator counter is `cap` instead of `stats_alloc`,
  so it also reports the running maximum: `net_max_heap_bytes`, which
  includes transients within an interval. It also records each catalog
  rebuild and engine compaction.
- **Timing build:** a plain release build, used for latency.
- **Workload:** fresh-ID churn of 5% per cycle, 100k nodes, seed 5000001.
- **Outputs:** in `raw/`, with binaries in `raw/binary-sha256.txt` and runs
  in `raw/runs.txt`. The summary is `summary.txt`, from `summarize.py`.
- **Fidelity.** With the frozen policy, the count build reproduces D2's
  30-cycle series byte for byte in all three topologies.
  - The first build differed by +192 B from cycle 20 on. That was the
    diagnostic event log, allocated at the first compaction.
  - The log is now pre-allocated before the baseline. The superseded runs
    are kept in `raw/superseded/`.
- Logical counts equal the model's at every checkpoint, in every run.

## Results (`summary.txt`)

**C3 over 30 cycles** (late/early ≤ 1.25, growth ≤ 0.10):

| | frozen | T1 | T2 |
|---|---|---|---|
| sparse | 0.927, +0.103 **FAIL** | 0.914, −0.021 **PASS** | 0.914, −0.021 PASS |
| ring | 0.950, +0.172 **FAIL** | 0.940, +0.037 **PASS** | 0.940, +0.037 PASS |
| hub | 0.927, +0.119 **FAIL** | 0.914, −0.006 **PASS** | 0.914, −0.006 PASS |

**B5 at 100k** (lifecycle/plain ≤ 3.0): sparse 2.4534 and hub 2.4425 in all
three policies. Construction is unchanged.

**6,000 cycles (300 compaction intervals):**

| | Running-max peak (MiB) | Checkpoint peak (MiB) | First-interval max / later interval max (MiB) | Last 100 cycles, mean (MiB) | Final `catalog_node_capacity` |
|---|---|---|---|---|---|
| sparse frozen | 43.294 | 33.519 (cycle 7) | 33.519 / 31.232 | 30.354 | 180,569 |
| sparse T1 | **38.169** | **28.394** (cycle 7) | 28.394 / 26.107 | **25.229** | 112,013 |
| ring frozen | 40.175 | 30.154 (cycle 19) | 30.154 / 28.870 | 28.054 | 176,848 |
| ring T1 | **35.050** | **25.029** (cycle 19) | 25.029 / 23.745 | **22.929** | 106,628 |
| hub frozen | 43.188 | 33.220 (cycle 8) | 33.220 / 31.119 | 30.354 | 180,569 |
| hub T1 | **38.063** | **28.095** (cycle 8) | 28.095 / 25.994 | **25.229** | 112,013 |

T2 has the same heap values as T1 to the byte.

**Ring-drift classification (declared).** Least-squares slope of the
per-interval maxima, with a 95% interval:

| | Intervals 2–150 | Intervals 151–300 (decides) |
|---|---|---|
| sparse (all policies) | −76.6 B/interval [−143.8, −9.4] | +6.8 [−46.1, +59.7]: **bounded** |
| ring (all policies) | +69.4 [+27.8, +111.0]: cumulative over this early span | +4.4 [−27.4, +36.1]: **bounded** |
| hub (all policies) | −5.3 [−52.4, +41.8] | +6.8 [−46.1, +59.7]: **bounded** |

**Event counts** (deterministic, count build):
- T1: 972 catalog rebuilds per 6,000 cycles (about one per 6 cycles).
- T2: 901 rebuilds on grow, plus 300 after compaction.
- Engine compactions: 300 in every variant.

The event *durations* recorded by the count build are **not used**. They
were collected while other runs and builds were active (addendum 1, A1).

**Latency** (timing build, quiet phase-3 chain, `summary-latency.txt`;
median / p99 / max, ms):

| | Catalog rebuild (T1) | Engine compaction, frozen | Engine compaction, T1 |
|---|---|---|---|
| sparse | 0.72 / 0.91 / 0.97 | 15.9 / 18.0 / 19.7 | 13.5 / 19.2 / 22.8 |
| ring | 0.72 / 1.24 / **6.49** | 13.4 / 17.3 / 22.0 | 10.9 / **31.1** / **37.9** |
| hub | 0.71 / 0.87 / 1.76 | 14.9 / 18.4 / 27.3 | 13.4 / 18.0 / **72.3** |

Disclosed overlap: a low-priority summary script (a few seconds) ran during
the first latency run (frozen ring).

**Impact on operations** (addendum 1, A2: B1 fresh-churn cells, same timing
binary, runs in the order frozen, T1, T1, frozen, 24 pairs per policy):

| Cell | Lifecycle window, frozen | Lifecycle window, T1 | Lifecycle/reference, frozen → T1 |
|---|---|---|---|
| sparse 1k | 1,960.8 µs | 1,968.7 µs (+0.4%) | 0.614 → 0.618 |
| sparse 10k | 12,017.3 µs | 11,981.8 µs (−0.3%) | 0.984 → 0.982 |

**The product change reproduces the diagnostic** (addendum 1, A3,
`summary-product.txt`).
- Setup: the frozen `core-lifecycle` (unmodified, `stats_alloc`) built
  count-alloc against the candidate with the product T1 and no diagnostic
  code (knotrel `f34af87d`, binary in `raw/product/binary-sha256.txt`).
- Result: the same `net_heap_bytes`, catalog and engine counts at every
  checkpoint as the diagnostic T1, **byte for byte**. That holds for 30
  cycles (3 topologies), 6,000 cycles (3 topologies) and B5 (sparse, hub),
  and logical counts equal the model.

## What this demonstrates

1. **T1 removes the cause of the C3 FAILs.** It is a product change, not a
   rule or window change. Without growing the catalog, C3 passes in all
   three topologies, with B5 unchanged.
2. **Memory falls everywhere, by about 5.1 MiB:**
   - the running-max peak (which includes the transient while two tables
     coexist);
   - the checkpoint peak;
   - the steady state.

   The frozen table doubles and then carries tombstones: final capacity
   about 180,000 against about 112,000.
3. **Transient and steady state, both measured.**
   - The first interval is still the highest: about 2.3 MiB (sparse, hub)
     and 1.3 MiB (ring) above the later interval maxima.
   - After that the heap stays in a band.
   - The ring drift is **bounded** by the declared classification: the slope
     over intervals 151–300 has an interval that includes 0. Its early
     positive slope (intervals 2–150) does not continue.
   - Serial correlation is not modelled; this is disclosed in the plan.
4. **T2 adds nothing to C3.** It lowers the engine-compaction maximum and
   adds 300 rebuilds. By the declared rule, T1 is chosen.

## Criterion to include T1 in the candidate (plan, D2c)

| | Criterion | Status |
|---|---|---|
| 1 | C3 PASS in all three topologies | met |
| 2 | B5 ≤ frozen + 0.01× | met (equal) |
| 3 | 6,000-cycle peak ≤ frozen in every topology | met (−5.1 MiB) |
| 4 | max rebuild duration ≤ max engine-compaction duration, same run | met on the timing build: 0.97 against 22.8 ms (sparse), 6.49 against 37.9 (ring), 1.76 against 72.3 (hub) |
| 5 | knotrel tests, Clippy, Rustdoc with the change and new unit tests | met at `f34af87d`; see below |

**Criterion 5 in detail** (`f34af87d`):
- `cargo fmt --check`, Clippy (`-D warnings`), Rustdoc (`-D warnings`) and the
  `knotrel-core` MSRV check (`cargo +1.98.1 check -p knotrel-core`) pass.
- The workspace tests pass: 380 passed, 0 failed.
- **One flaky failure.** A first full run stopped on
  `e2e_rebuild::test_07_lease_expiry…`: its server process exited with
  `AddrInUse` (a port collision between parallel tests). The test then
  passed 5 times out of 5 on its own, and the whole suite passed on the next
  full run. It is unrelated to the change.
- **Two new unit tests:**
  - fresh-ID churn at 89% of the catalog's capacity: no growth, rebuilds
    happen, state preserved;
  - growth of live entries: the catalog still grows.

**Addendum 1 condition (A2):** T1 must not slow the lifecycle arm by more
than 25% by median in either B1 cell. It is met: +0.4% and −0.3%.

## Decision on T1 (proposed, reasoned)

**Adopt T1 in the candidate.**
- **It meets every declared criterion,** with no rule or window change.
- **It removes the measured cause of the C3 FAILs.** The catalog doubling at
  cycle 5 is gone, and C3 passes in all three topologies.
- **It lowers memory and leaves construction alone.** The transient peak,
  which includes the moment two tables coexist, and the steady state both
  fall by about 5.1 MiB at 100k. Construction and B5 are unchanged.
- **Its cost is small and bounded.** One O(V) table rebuild about every 6
  cycles: median 0.7 ms, max 6.5 ms. Throughput in the B1 fresh-churn cells
  is unchanged within ±0.5%.
- **It is the measured behaviour.** Byte-for-byte reproduction shows the
  product code behaves as the diagnostic variant did.

**Residual uncertainty**, disclosed:
- **Compaction tails.** In the T1 timing runs the engine-compaction tails
  were higher on ring (p99 31.1 against 17.3 ms; max 37.9 against 22.0) and
  on hub (max 72.3 against 27.3 ms), with lower medians.
  - T1 does not change the compaction code, and the catalog it iterates is
    smaller. The tails are single-run outliers on an ungated laptop.
  - No mechanism for an increase was found. This is not demonstrated either
    way.
- **One n only.** The 90% bound and the gain depend on the table's
  power-of-two sizing; they are shown at 100k (and in the unit test at
  3,200 entries).
