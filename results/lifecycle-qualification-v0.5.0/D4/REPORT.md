# D4 — memory bounds on candidate a1d9577 (diagnostic)

Plan: `../D4-PLAN.md` (frozen, with pre-execution addendum). 39 runs, all exit
0, all on AC power, 242.8 s measured (cap 900 s). Tools: read-only copies
`../D4-bin/memory-peak` (`451702f2…`, knotrel `a1d9577`, probes `00bd886e`,
clean) and `../D4-bin/core-lifecycle-count` (`53497c21…`, knotrel `a1d9577`,
probes `444806d3`, clean). Raw: `raw/`; run log: `run-log.json`.
**D4 changes no historical verdict: the 16 run-3 C3 FAILs stand.**

Metric definitions: *live heap* = bytes currently requested from the global
allocator; *peak* = running maximum of live heap (`cap`), reallocations at
their resulting size, allocator-internal copies and metadata excluded, not
resettable; *retained capacity* = vector/table capacity beyond logical size
(structural counters); *RSS* = `ps` resident size, includes allocator
retention. "net" = minus the baseline before building the graph.

## D4a — churn with peak tracking (lifecycle arm, sparse, 100k, 30 cycles)

Validity: logical counts equal the expected counts and run 3's checkpoints at
every cycle in all 9 runs; live heap equals run 3's `stats_alloc` values.

| Engine / reuse | net live: first → max → last (MiB) | net peak (MiB) | peak − max checkpoint live | where the peak rose | RSS at cycle 30 |
|---|---|---|---|---|---|
| compact-bfs fresh | 23.0 → 37.3 → 34.5 | 49.2 | +11.9 | cycle 20 (compaction) | 106 MiB |
| compact-bfs same | 23.0 → 24.1 → 24.1 | 27.0 | +2.9 | before cycle 1 | 86 MiB |
| compact-bfs toggle | 23.0 → 23.0 → 23.0 | 23.0 | 0.0 | construction | 66 MiB |
| ett fresh | 70.3 → 91.3 → 79.6 | 150.6 | +59.3 | cycle 20 (compaction) | 186 MiB |
| ett same | 70.3 → 80.0 → 78.6 | 90.3 | +10.3 | cycle 8 (hash-table resize) | 150 MiB |
| ett toggle | 70.3 → 70.3 → 69.4 | 70.4 | +0.1 | cycle 2 | 114 MiB |
| hdt fresh | 99.1 → 241.9 → 189.1 | 338.1 | +96.1 | cycle 20 (compaction) | 241 MiB |
| hdt same | 99.1 → 223.6 → 223.4 | 224.9 | +1.4 | cycle 8 | 266 MiB |
| hdt toggle | 99.1 → 182.3 → 182.3 | 183.9 | +1.6 | cycle 30 | 191 MiB |

Compaction (one per run, at cycle 20, when retired slots exceeded the
registered nodes) holds the old engine, the new engine and the order/effective
vectors at once: the transient exceeds the largest checkpoint live heap by
32% (compact-bfs), 65% (ett) and 40% (hdt). Cycle-boundary checkpoints (C3,
B5) never saw these peaks.

## D4b — plateau check on the exact candidate (120 cycles, D2's frozen rule)

All 17 cells: counts correct; 14 PLATEAU and 3 BOUNDED_SAWTOOTH, the same
classification as D2 (which ran on `1ec2de3` with dirty probes). Example: hdt
sparse toggle 100k max heap 200.8 / 201.1 / 202.6 MiB over cycles 31-60 /
61-90 / 91-120.

## D4c — HDT levels at engine level (120 cycles, same schedules)

The schedules' effective-graph changes applied directly to `HdtGraph` (engine
edge count checked against the model every cycle). Operation order differs
from the facade's (the replay iterates a hash set; the facade cuts in
descending neighbor order).

| Topology / reuse | net live c30 → c60 → c90 → c120 (MiB) | vector capacity c30 → c120 | levels | L3 record slots c30 → c120 |
|---|---|---|---|---|
| ring same | 200.2 → 200.1 → 200.3 → 200.5 | 140.7 → 141.0 | 6 → 7 | 34k → 36k |
| ring toggle | 190.0 → 192.4 → 192.1 → 192.4 | 147.6 → 149.9 | 8 | 49k → 56k |
| sparse same | 236.2 → 236.3 → 241.0 → 240.3 | 140.2 → 144.8 | 6 → 7 | 29k → 39k |
| sparse toggle | 182.8 → 190.9 → 199.2 → **215.6** | 122.1 → **154.0** | 6 → 8 | 22k → 47k |

Live payload (ordered-container data) stays flat (about 25 MiB sparse, 16 MiB
ring); growth is retained vector capacity and record slots at upper levels.
**Engine-level sparse toggle did not plateau within 120 cycles** (+18% from
cycle 30 to 120), while the facade-level D4b cell plateaued. HDT steady-state
memory therefore depends on operation order and history; the D4b plateaus are
observations for the measured schedules, not a general property.

## D4d — import peaks (one process per run)

| Run | live before → after (MiB) | peak (MiB, exact) | transient over final |
|---|---|---|---|
| core compact-bfs 100k 20/10 | 6.4 → 25.5 | 28.2 | +2.8 |
| core compact-bfs 100k 60/30 | 6.4 → 23.6 | 24.8 | +1.3 |
| core ett 10k 20/10 | 0.6 → 5.7 | 6.1 | +0.4 |
| core hdt 10k 20/10 | 0.6 → 7.8 | 8.6 | +0.8 |
| HTTP create compact-bfs 100k 20/10 (body 8.3 MiB) | 20.5 → 24.3 | 111.2 | +87.0 |
| HTTP create compact-bfs 100k 60/30 (body 9.9 MiB) | 20.5 → 22.4 | 128.6 | +106.2 |
| HTTP create ett 10k 20/10 | 3.0 → 6.5 | 11.9 | +5.3 |
| HTTP create hdt 10k 20/10 | 3.0 → 8.6 | 11.9 | +3.2 |
| HTTP replace compact-bfs 100k 20/10 (old graph live) | 39.5 → 24.3 | 130.3 | +106.0 |

The core build adds little transient memory; the HTTP import's transient
(about 11-13× the body at 100k) arises before or around the build (request
buffering and deserialization into wire records, spec vectors, then the
candidate graph while the old graph is still published). Whether the plain
(lifecycle-disabled) import has a similar transient was not measured.

## Classification

1. **Bounds from code invariants:** engine slots ≤ 2V + 1024 between
   operations (compaction rule); HDT record slots per level ≤ that level's
   historical peak of live records ≤ engine vertices (slot reuse); HDT edge
   tokens per level ≤ peak live tokens (free-list reuse); HDT levels ≤
   ⌊log₂U⌋ + 1 (component-size invariant; `debug_assert` and test validation
   only; observed ≤ 8 of 18); incident-list capacity ≤ max(4 × length,
   `MIN_SHRINK_CAPACITY`); emptied incidence sets hold no node.
2. **Observed maxima (this host, these schedules):** the tables above,
   including compaction peaks (49 / 151 / 338 MiB net at 100k) and HTTP import
   peaks (111-130 MiB at 100k).
3. **Retained capacities:** vectors and hash tables never shrink except
   incident lists; HDT vector capacity reached 154 MiB at engine level; the
   catalog table doubled under fresh-ID churn (114,688 → 229,268 capacity).
4. **Not guaranteed:** RSS (allocator retention; 66-266 MiB at cycle 30; no
   hard bound in the product); a practical steady-state level for HDT heap
   (D4c's sparse toggle replay kept growing through cycle 120 on that one
   path, mostly token-arena capacity stepping to larger power-of-two sizes at
   levels 2 and 3 while stored data stayed flat; this is continued growth on
   one path, not a demonstrated leak or unbounded structure); peak heap for
   inputs or schedules not measured; behavior beyond 120 cycles.

**Correction (2026-11-16).** Earlier wording in this report and in the
release notes called HDT steady-state heap "not bounded". The code bounds
specific structures: per level at most `V + 2(V − 1)` Euler-tour tokens and
`V` record slots, with at most `⌊log₂ U⌋ + 1` levels (`U ≤ 2V + 1024` with
lifecycle slots); vector capacity follows the standard library's growth
policy, an implementation property rather than a guarantee. That is a bound
on those arenas and records, not on total process memory, which also
includes incidence sets, mapping and edge hash tables, the lifecycle
catalog, allocator overhead and RSS retention. No total ceiling is claimed.
