# knotrel#182 BFS regression diagnosis: report

Protocol: [`PROTOCOL.md`](PROTOCOL.md), committed (b9f174d0, 2026-11-27 15:01 +01:00) before
the first diagnostic run (15:02).

- Attempt 1 of #182 stays valid.
- Candidate 9faf168 stays **not qualified**.
- Frozen thresholds and classes are unchanged.
- Nothing here is a qualification verdict.
- Host time used: under 5 minutes of the 30 allowed. Swap counters were 0 before and after
  (`swap.txt`).

## Summary

1. **The slowdowns are a per-layer constant cost, not extra search work.**
   - On the regressed traces (chain, cycle, components, sustained-path), the bidirectional
     search examines **the same number of adjacency entries** as the v1.1.0 search
     (W = 0.99–1.00). Components-join-split connected queries examine fewer (W = 0.63).
   - Yet each entry costs **1.5–3.1× more**: 3.3–4.0 ns against 1.3–2.2 ns.
   - These traces expand about **2 entries per layer**, because each frontier is one or two
     vertices wide on a path. So the fixed work of every layer dominates: the clear and swap
     of the frontier vectors, the side choice, the `pending` degree read of each new vertex,
     and the second bitset test.
   - Where layers are wide (sustained-blocks, about 10–30 entries per layer), the per-entry
     cost is 0.96–1.32× and time is within ±5 %, except sustained-blocks 10k disconnected
     queries at 1.18×.
2. **The gains are real and come from the algorithm.**
   - On low-diameter graphs (hub, dense and redundant bridges, and the #181 random,
     ring-with-chords and hub topologies) the search meets early.
   - Work falls by 70× to effectively zero (hub-alternatives disconnected queries: 0
     entries, because the isolated side is exhausted at once). Time falls 15× to over 800×.
3. **`compact-workspace`: the BFS change does not touch its executed code.**
   - `connected_with_workspace` has **identical machine code** in all four harness builds
     (V1 pair and K1 pair). Only its address changes, by +68 bytes (V1) and +132 bytes (K1).
   - The timing difference does not reproduce consistently. V1 binaries: +4 % on connected
     queries now, against +17 % in attempt 1. K1 binaries: +17 %.
   - Under the declared rule H-layout is **unresolved**. The code-placement explanation is
     consistent with the data but not proven.
4. **Recommendation:** keep the bidirectional BFS and make a **circumscribed fix** of its
   per-layer overhead (details at the end). Do not revert, and do not add an adaptive switch.

## 1. #181 against #182: what is comparable

| | #181 (impact estimate, A) | #182 K1 | #182 V1 core |
|---|---|---|---|
| Baseline code | knotrel cd57816 = v1.1.0 for `knotrel-core` and `knotrel-server` (empty diff from 57c35e8) | v1.1.0 57c35e8 | v1.1.0 57c35e8 |
| Candidate code | 1daee1b = 9faf168 for `lib.rs` (empty diff) | 9faf168 | 9faf168 |
| Harness | `lifecycle-probes` `core-lifecycle pairs --exp ops --mix query` at 8a47e5ca | `knotrel-benchmarks` harness at 4cf9b103, same source both arms | v1.0.0 A harness df635a1e, same source both arms |
| Path | `LifecycleGraph` with compact-bfs engine to `Graph::connected` | `ConnectivityGraph` with compact-bfs to `Graph::connected` | `Graph::connected` directly; `compact-workspace` cell: `connected_with_workspace` |
| Topologies | random sparse (2N random edges), ring + 1/64 random chords, ring + hubs of 2000 random spokes: all **low diameter** | chain, cycle, two half-chains, hub fan, sustained path and blocks, dense and redundant bridges | chain-split-rejoin and sustained-churn-path, 10k |
| Query pairs | uniform random pairs | **fixed extremes**: chain (0, N−1); cycle (v, v+N/2); components (0, N−1); hub (0, v) | as K1 |
| Connected / disconnected | not recorded. Inferred mostly connected: giant component, ring and hub connected | recorded: chain and components 50/50, cycle 3:1, hub 5:1 | recorded, 50/50 |
| Timed operations | lifecycle window of 4000 operations (90 % queries; rest flags, remove/add, link, cut) | queries plus link and cut (link and cut ≤ 0.04 ms, unchanged) | same |
| Workspace | not used | not used | used only by the `compact-workspace` cell |

**Comparability.**
- #181 A and #182 K1/V1 test the **same code change** on the **same baseline code**, but
  in **disjoint graph regimes**: #181 has low diameter and random pairs, #182 has path-like
  graphs with pairs at the extremes. Neither contradicts the other.
- The #182 cells comparable to #181's regime are:
  - the B4 query cells on sparse and hub 10k, all PASS (HTTP-bound);
  - K1 hub-alternatives, dense-bridge and redundant-bridge, all faster.
- #181 B and #182 Q measure the same thing: the feeder's L2 G100k share at C=16.
  - #181 candidate: 43.7 %; #182: 48.5 %.
  - C=0 rate: 177,960 events/s in #181, 173,131 in #182.

**Absolute times** (medians):

| Cell | v1.1.0 | candidate | ratio |
|---|---|---|---|
| #181 sparse 100k, window of 4000 ops | 2,340 ms | 19.0 ms | 0.008 |
| #181 hub 100k | 1,469 ms | 15.9 ms | 0.011 |
| #182 K1 hub-alternatives 100k (wall) | 208.0 ms | 1.6 ms | 0.008 |
| #182 K1 redundant-bridge 2048 (wall) | 1,577 ms | 434 ms | 0.28 |
| #182 K1 chain-split-rejoin 100k, connected queries ×100 | 25.6 ms (256 µs each) | 78.7 ms (787 µs each) | 3.07 |
| #182 K1 chain-split-rejoin 100k, disconnected queries ×100 | 12.7 ms | 38.3 ms | 3.01 |
| #182 V1 sparse traversal (chain 10k) compact-bfs, connected ×100 | 3.24 ms | 6.74 ms | 2.08 |
| #182 V1 sparse traversal (chain 10k) compact-workspace, connected ×100 | 3.62 ms | 4.22 ms | 1.17 |

## 2. The three focus cases

### chain-split-rejoin 100k (K1, +190 % to +213 %)

- **Trace.** A 100,000-vertex path. Each round cuts one edge, queries (0, 99,999) (false),
  relinks it and queries again (true).
- **v1.1.0.** The search walks from 0 to the far end or to the cut.
- **Bidirectional.** It walks from both ends and meets in the middle or exhausts the shorter
  piece. **D1: identical entry counts** (W = 1.000 for true and false).
- **D2.** Per-entry cost 1.28–1.32 ns (v1.1.0) against 3.94–3.96 ns (candidate): c = 3.0,
  with 2.0 entries per layer. Verdict **H-const**.

### Sparse traversal, `compact-bfs` (V1, +92 % to +121 %)

- It is the same chain-split-rejoin workload at 10k, through `Graph::connected` directly.
- W = 1.000, c = 1.96 (false) and 2.08 (true), 2.0 entries per layer. Verdict **H-const**.

### Sparse traversal, `compact-workspace` (V1, +7 % to +18 %)

- **Path actually executed.** The harness dispatches `Storage::CompactWorkspace` to
  `Graph::connected_with_workspace` (`engines.rs`, both harness revisions). That function
  lives in `workspace.rs`, which is absent from the v1.1.0 to 9faf168 diff. It does not call
  `Graph::connected`; link and cut are unchanged too.
- **D3.**
  - The 236-instruction body, with branch targets taken relative to the function start, is
    **identical** in A-B against A-C and in base against cand.
  - The start moves 0x…e84 to 0x…ec8 (mod 64: 4 to 8) in V1, and 0x…7a4 to 0x…828
    (36 to 40) in K1.
- **D4** (12 alternating pairs each). Median ratio, with the [r3, r10] range of the pair
  ratios:

  | Binaries | Connected queries | Disconnected queries |
  |---|---|---|
  | V1 (A-B/A-C) | 1.04 [0.99, 1.20] | 1.01 [0.98, 1.09] |
  | K1 (base/cand) | 1.17 [1.04, 1.24] | 1.07 [1.02, 1.13] |

- **Rule outcome: unresolved.**
  - The protocol expected the K1 pair to show no difference and the V1 pair to reproduce
    ≥ 1.07. The opposite happened.
  - The machine code is the same. The candidate-linked builds tend to be slower on this
    loop, by a varying amount.
  - That points to code placement or front-end alignment, not to the change's logic. It is
    not proven.
- **Consequence.** This effect is not a property of either BFS. Any candidate that
  re-links `knotrel-core` can show it.

## 3. Results table (D1, D2)

Full data: `work.json` (D1), `d2.json` and `d2.txt` (D2).

- R = time ratio, candidate over v1.1.0. W = adjacency entries examined, same ratio.
- c = cost per entry, same ratio. Layer = entries per layer in the candidate.

| Source | Workload | N | Queries | R | W | ns/entry v1.1.0 → cand | c | Layer | Rule |
|---|---|---|---|---|---|---|---|---|---|
| K1 | chain-split-rejoin | 10k | false | 2.52 | 1.000 | 1.60 → 4.04 | 2.52 | 2.0 | H-const |
| K1 | chain-split-rejoin | 10k | true | 2.70 | 1.000 | 1.48 → 3.99 | 2.70 | 2.0 | H-const |
| K1 | chain-split-rejoin | 100k | false | 3.01 | 1.000 | 1.32 → 3.96 | 3.01 | 2.0 | H-const |
| K1 | chain-split-rejoin | 100k | true | 3.07 | 1.000 | 1.28 → 3.94 | 3.07 | 2.0 | H-const |
| K1 | components-join-split | 10k | false | 1.76 | 1.000 | 2.23 → 3.93 | 1.76 | 2.0 | H-const |
| K1 | components-join-split | 10k | true | 1.28 | 0.633 | 1.75 → 3.52 | 2.01 | 2.0 | H-const |
| K1 | components-join-split | 100k | false | 2.25 | 1.000 | 1.69 → 3.81 | 2.25 | 2.0 | H-const |
| K1 | components-join-split | 100k | true | 1.32 | 0.629 | 1.54 → 3.25 | 2.11 | 2.0 | H-const |
| K1 | cycle-alternatives | 10k | true | 1.62 | 1.000 | 1.86 → 3.00 | 1.62 | 2.7 | H-const |
| K1 | cycle-alternatives | 100k | true | 1.89 | 1.000 | 1.54 → 2.90 | 1.89 | 2.7 | H-const |
| K1 | sustained-churn-path | 10k | false | 1.46 | 0.990 | 3.34 → 4.91 | 1.47 | 2.6 | mixed (c just under 1.5) |
| K1 | sustained-churn-path | 10k | true | 1.40 | 0.999 | 2.42 → 3.39 | 1.40 | 2.6 | mixed (c just under 1.5) |
| K1 | sustained-churn-path | 100k | false | 1.54 | 0.998 | 2.12 → 3.28 | 1.54 | 2.7 | H-const |
| K1 | sustained-churn-path | 100k | true | 1.46 | 1.000 | 1.61 → 2.35 | 1.46 | 3.5 | mixed (c just under 1.5) |
| K1 | sustained-churn-blocks | 10k | false | 1.18 | 0.898 | 2.80 → 3.70 | 1.32 | 10.7 | mixed |
| K1 | sustained-churn-blocks | 10k | true | 1.05 | 1.002 | 1.95 → 2.05 | 1.05 | 21.3 | ≈ unchanged |
| K1 | sustained-churn-blocks | 100k | false | 1.02 | 0.956 | 1.75 → 1.87 | 1.07 | 19.7 | ≈ unchanged |
| K1 | sustained-churn-blocks | 100k | true | 1.04 | 1.086 | 1.57 → 1.51 | 0.96 | 29.3 | ≈ unchanged |
| K1 | redundant-bridge-churn | 512 | false | 1.14 | 1.004 | 0.63 → 0.72 | 1.14 | 21,845 | H-work by the rule (W ≥ 0.8 R); a small per-entry cost |
| K1 | redundant-bridge-churn | 512 | true | 0.06 | 0.014 | — | — | 205 | faster |
| K1 | hub-alternatives | 10k | true | 0.004 | 0.0001 | — | — | 1.2 | faster |
| V1 | chain-split-rejoin | 10k | false | 1.97 | 1.000 | 1.72 → 3.38 | 1.96 | 2.0 | H-const |
| V1 | chain-split-rejoin | 10k | true | 2.08 | 1.000 | 1.62 → 3.37 | 2.08 | 2.0 | H-const |
| V1 | sustained-churn-path | 10k | false | 1.49 | 0.990 | 3.02 → 4.55 | 1.50 | 2.6 | H-const |
| V1 | sustained-churn-path | 10k | true | 1.44 | 0.999 | 2.18 → 3.15 | 1.44 | 2.6 | mixed (c just under 1.5) |

Other D1 counts:
- hub-alternatives disconnected queries: v1.1.0 examines 3,998,800 entries, the candidate 0.
- cycle-alternatives disconnected queries: 0 for both (the queried vertex is isolated).

**D1 validation.** Every replayed answer equals the trace's `expected` in all 12 traces,
so the work model is not void.

**Reading.**
- No regressed trace does more work under the bidirectional search; the largest W in any
  trace is 1.09.
- The disconnected-pair risk named in the #181 protocol, a small component queried into a
  large one, does not occur in these traces. Where it occurs (hub), the bidirectional search
  wins outright.

## 4. Recommendation for the next candidate

**Keep the bidirectional BFS, with a circumscribed fix of the per-layer overhead.**

The data favour this option over the other two:

- **Revert to the v1.1.0 search.** It would remove the 10 regressions. It would also give
  up gains that come from search work, not implementation details:
  - #181 A: 0.008–0.23× time;
  - K1 hub-alternatives: 0.008×; redundant-bridge: 0.28–0.33×; dense-bridge: 0.59–0.60×;
  - the feeder's C=16 share would fall from 48.5 % back to about 15 % (#181 base), moving
    Q3 further from its threshold.
- **Adaptive choice.** It is not supported by the data. No trace does more work under the
  bidirectional search (W ≤ 1.09), so there is no regime that a unidirectional fallback
  would serve better in work. The losses are a constant factor of the implementation. A
  switch would keep that cost on the bidirectional branch and add a heuristic to tune.
- **Circumscribed fix** (an implementation change; answers, errors and O(V + E) unchanged).
  It targets the costs the data isolate:
  - one mark array for both sides (two bits or one byte per vertex, a single allocation),
    so one load answers both "mine" and "theirs";
  - per-side FIFO queues with a cursor and a layer boundary index, as in the v1.1.0 loop,
    instead of clearing and swapping frontier vectors every layer;
  - balance by remaining queue length instead of reading the degree of every newly marked
    vertex;
  - optionally, expand the chosen side for several layers while its frontier stays small,
    to amortize the side choice.

**What it should keep (to be shown by its impact estimate):**
- all work-driven gains (#181 A cells; K1 hub, dense and redundant bridges; the HTTP query
  cells);
- the Q improvement from 15 % to 48.5 %.

**What stays open:**
1. **The 10 deciding REGRESSIONs** stay open until a new candidate is qualified. The fix
   targets the per-entry cost (3.3–4.0 ns, against 1.3–2.2 ns for v1.1.0). Whether it
   reaches the frozen tolerances on the path-like cells is unknown until measured.
   - The impact estimate should include K1 chain-split-rejoin, cycle-alternatives,
     components-join-split and sustained-churn-path at 10k and 100k, plus the #181 A cells.
2. **The `compact-workspace` effect** (+4 % to +17 %, identical code, unresolved). No BFS
   choice addresses it. It needs a disposition, or a layout-robust check, before the next
   qualification.
3. **Q3 FAIL at 48.5 %.** No BFS choice is expected to close the gap to 50 % by itself. B2
   on #87 stays open: bounded concurrent query execution, designed on the chosen BFS.
4. **Not diagnosed here:**
   - the 2 TIMER_LIMITED cells (K1 sustained-churn 10k);
   - the 3 V1 inconclusive or unresolved cells;
   - the descriptive B4 `import-high` sparse 10k REGRESSION ([+386, +441] %).
