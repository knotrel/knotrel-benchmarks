# D2b: partial pre-sizing and a 1,500-cycle run (item 2, phase 2)

This diagnostic follows DIAGNOSTICS-PLAN-2.md, D2b. It is not part of the
qualification. The a3-3 C3 FAILs stand, and no threshold changes.

**Setup.**
- **Build:** a diagnostic build of candidate e75ff6a (`d2b-core.diff`, plus
  `d2b-probe.diff` on the frozen probes).
- **Pre-sizing policy:** a component policy (catalog, engine ID map,
  adjacency header array), given as factors of the registered node count.
  - In the probe it applies right after `LifecycleGraph::new`, through the
    env `KNOTREL_D2B="catalog,ids,headers"`.
  - It applies at the end of a bulk import, which is the server path.
  - The engine part applies again after each compaction.
- **Workload:** the frozen `core-lifecycle resources` workload: count-alloc
  build, lifecycle arm, fresh-ID churn of 5% per cycle, 100k nodes, seed
  5000001.
- **Outputs:** in `raw/`, with binaries in `raw/binary-sha256.txt`.
- **Build stamp:** `fc56693`, dirty, `probes_rev: unknown`. That is a scratch
  snapshot whose tree equals e75ff6a's, plus `d2b-core.diff`. The probes are
  f73c2bd plus `d2b-probe.diff`, in a copy without git history. The
  summaries come from `summarize.py`, `summarize_import.py` and
  `summarize_long.py`.
- **Fidelity check.** With no policy, this build reproduces D2's frozen
  series byte for byte (30 and 300 cycles, all three topologies). With
  policy `2,2,2` it reproduces D2's presized-start series byte for byte.
- In every run, the logical counts equal the model's at every checkpoint.

## Results (`summary.txt`, `summary-import.txt`)

| Variant (catalog, ids, headers) | C3 sparse | C3 ring | C3 hub | B5 sparse (≤ 3×) | B5 hub (≤ 3×) | Peak, 300 cycles (MiB) | Import time, variant/frozen | Import net heap |
|---|---|---|---|---|---|---|---|---|
| frozen (0, 0, 0) | FAIL (+0.103) | FAIL (+0.172) | FAIL (+0.119) | 2.453 | 2.442 | 33.52 / 30.15 / 33.22 | — | 18.69 MiB |
| **cat (2n, 0, 0)** | **PASS (−0.017)** | **PASS (+0.030)** | **PASS (−0.005)** | **2.9999992** | **2.9999992** | 33.52 / 30.15 / 33.22 | 1.035 (0.957–1.075) | +5.12 MiB |
| ids (0, 2n, 0) | PASS (+0.091) | FAIL (+0.157) | FAIL (+0.106) | 2.680 | 2.674 | 33.52 / 30.15 / 33.22 | 1.007 | +2.12 MiB |
| hdr-1.25 | PASS (+0.099) | FAIL (+0.168) | FAIL (+0.114) | 2.439 | 2.427 | 33.27 / 29.88 / 32.94 | 1.015 | +2.29 MiB ¹ |
| hdr-1.5 | FAIL (+0.123) | FAIL (+0.198) | FAIL (+0.139) | 2.500 | 2.490 | 34.27 / 31.02 / 34.06 | 1.016 | +2.29 MiB ¹ |
| hdr-2 | PASS (+0.072) | FAIL (+0.135) | PASS (+0.086) | 2.622 | 2.614 | 32.13 / 28.86 / 31.80 | 1.014 | +2.29 MiB |
| eng (0, 2n, 2n) | PASS (+0.060) | FAIL (+0.121) | PASS (+0.074) | 2.848 | 2.845 | 32.13 / 28.86 / 31.80 | 1.015 | +4.41 MiB |
| full (2n, 2n, 2n) | PASS | PASS | PASS | 3.395 FAIL | 3.403 FAIL | 32.13 / 28.86 / 31.80 | 1.030 | +9.54 MiB |

How to read the table:
- C3 shows the 30-cycle growth (the rule is ≤ 0.10). Late/early is within
  1.25 in every variant.
- B5 is lifecycle/plain net heap after construction.
- Import time is the median of 24 pairs, with the pair min–max where shown.
  The import graph is 100k sparse, all active, through `try_from_topology`.

¹ **Disclosed artefact.** The header policy uses `Vec::reserve`, which
grows amortized: when the vector is not empty it doubles. Consequences:
- **On the import path,** 1.25n and 1.5n become 2n.
- **In the probe path,** the factor is exact at construction, but not later:
  - when the vertex count passes 1.5n (around cycle 11), the hdr-1.5 header
    vector doubles to 3n. That makes it worse than frozen in the C3 window;
  - from the first compaction (cycle 20), the reapplied policy amortizes to
    2n. hdr-1.5 then equals frozen for cycles 20–30.
- The partial header factors are therefore exact only up to the first
  growth or compaction.

## What this demonstrates

1. **Cause of the C3 FAILs: the catalog hash table grows during the first 30
   cycles.**
   - At 100,000 nodes the catalog holds 131,072 buckets (capacity 114,688).
     Fresh-ID churn inserts new keys and leaves tombstones, so the table
     grows to 262,144 buckets inside the C3 window.
   - The checkpoints record it in every topology. `catalog_node_capacity`
     falls from 114,688 to about 102,200 over cycles 1–4 as tombstones
     accumulate, then jumps to 229,376 at cycle 5. Under "cat" it is
     229,376 from cycle 0.
   - Reserving that size at construction ("cat") is the only change, and C3
     then passes in all three topologies. The 300-cycle peak, the
     steady-state mean and every later value are identical to frozen.
   - So the frozen build already reaches that size during churn; "cat" only
     moves the growth to construction.
2. **The cost of "cat" is +5.12 MiB at construction.** B5 becomes
   29,492,656 / 9,830,888 = 2.9999992× (sparse) and 28,917,328 / 9,639,112 =
   2.9999992× (hub). That is **8 bytes under** the 3.0× budget
   (`lifecycle <= 3.0 * plain`).
   - This is not a coincidence of this run. The edge-dependent memory is
     exactly three times plain (16 B catalog incidence plus 8 B engine
     adjacency, against 8 B plain), so the margin is set by fixed per-node
     sizes.
   - Any extra per-graph allocation, or a different n, can reverse it. This
     margin is not robust.
3. **Import cost.**
   - "cat" adds +3.5% to import time (pair range −4.3% to +7.5%) and
     +5.12 MiB of import heap.
   - The other variants add +0.7% to +3.0% to time, with pair ranges that
     include 0.
4. **Engine-only pre-sizing does not fix ring.** The engine variants (ids,
   hdr, eng) leave ring above 0.10. In the ring topology, the catalog
   growth is enough to fail C3 on its own.
5. **No variant measured passes both C3 and B5 with a margin.** "cat" passes
   both, by 8 bytes on B5.

## 1,500-cycle run (`summary-long.txt`; frozen and cat)

| | Bounded (halves rule: max part / slope part) | Ring-drift criterion (last 25 interval maxima ≤ max of intervals 26–50) | Slope of interval maxima, intervals 2–75 | Interval maxima 2–75: range / SD | Peak |
|---|---|---|---|---|---|
| sparse | **bounded** (max −128,144 B / slope +0.058%) | NOT settled (+15,400 B) | −7.6 KiB per 1,000 cycles | 178,000 / 21,992 B | 33.52 MiB, cycle 7 |
| ring | NOT bounded (max +7,128 B / slope +0.044%) | NOT settled (+8,520 B) | **+12.5 KiB per 1,000 cycles (+0.042%)** | 106,712 / 14,037 B | 30.15 MiB, cycle 19 |
| hub | NOT bounded (max +7,184 B / slope +0.059%) | NOT settled (+15,400 B) | +6.3 KiB per 1,000 cycles | 55,864 / 12,066 B | 33.22 MiB, cycle 8 |

The slope part is within ±1% of the early mean (the mean of cycles 1–10) in
every topology. The max part decides. The full per-interval maxima series
for every topology and variant is in `summary-long.txt`.

"cat" gives the same maxima to the byte. Its slopes differ by at most
0.004 percentage points.

- **The peak is set in the first interval, before the first compaction, in
  every topology.** Across 75 compactions, no later value reaches it. The
  first interval's maximum exceeds every later interval maximum by 1.3 MiB
  (ring) to 2.3 MiB (sparse).
- **After that the heap moves in a band.** Ring's interval maxima span
  30,160,728–30,267,440 B (0.35%). Their least-squares trend is +256 B per
  interval (+12.5 KiB per 1,000 cycles), and its minima trend is similar
  (+228 B per interval). On sparse the trend is negative (−7.6 KiB) and on
  hub +6.3 KiB.
- **Ring and hub fail the declared criteria by a few kilobytes,** while
  sparse is bounded by the halves rule but fails the drift criterion. The
  interval maxima have an SD of 12–22 KB. The ring drift is **not settled by
  the declared criterion** within 1,500 cycles. Its trend is +0.04% per
  1,000 cycles. Where it comes from (for example catalog tombstones or
  incident vector capacities) is not demonstrated.

## Limits

- **Deterministic counts, one host.** The import times come from one run of
  24 pairs per variant on an ungated laptop.
- **Pre-sizing is evaluated for one n (100,000).** The hash-table
  power-of-two steps make the cost and the B5 margin depend on n.
- **Allocator behaviour (RSS, C4) is not measured here.**
