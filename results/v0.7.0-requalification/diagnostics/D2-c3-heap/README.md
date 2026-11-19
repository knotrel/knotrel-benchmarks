# D2 — C3 heap growth FAIL ×3: repeated compaction cycles and pre-sizing cost

Diagnostic ordered on 2026-11-19 (DIAGNOSTICS-PLAN.md, D2). It is not part
of the qualification. The a3-3 C3 FAILs stand, and no threshold changes.

**Setup.** `core-lifecycle resources`, count-alloc builds (deterministic
allocator byte counts), lifecycle arm, `compact-bfs`, fresh-ID churn, 5% per
cycle, 100,000 nodes, seed 5000001. Outputs are in `raw/`; `summary.txt` is
produced by `summarize.py raw`, and the binaries are in
`raw/binary-sha256.txt`. One run per configuration (the counts are
deterministic). In every run, every checkpoint's logical counts equal the
independent model's.

## Variants

| Variant | Build | What changes |
|---|---|---|
| frozen | a3-3 candidate probe binary | — |
| presized-compaction | candidate + `presize.diff` | at each compaction (bulk rebuild), the engine ID map and adjacency header array are sized for twice the registered nodes, and the catalog gets the same headroom |
| presized-start | same build + `probe-presize.diff`, `KNOTREL_D2_PRESIZE=1` | additionally, the graph is pre-sized right after `new()`: catalog room for 2n nodes, engine room for 2n vertices (registered plus retired slots up to the compaction bound) |

`reserve_diagnostic` is a diagnostic hook, not a product API. The probe
builds the graph incrementally (`add_node`, `link`), so only presized-start
affects the first interval before the first compaction.

**Departures from the plan.**
- The plan asked for "catalog and incident tables pre-sized … sized from the
  300-cycle run". The diffs instead pre-size the catalog, the engine ID map
  and the adjacency header array, with a fixed factor of 2n (the compaction
  bound). The per-node incident vectors (`incident_capacity`) are not
  pre-sized.
- presized-compaction is an extra variant. It came from the first build, in
  which the hook only applied at compaction because the probe builds
  incrementally.

## 1. Bounded over repeated compaction (300 cycles, 10× the qualification)

- A compaction occurs every 20 cycles (15 in 300 cycles). After each one,
  retired slots return to 0 and the engine holds exactly the 100,000
  registered vertices.
- **Peak.** The overall peak falls in the **first** interval, before the
  first compaction: 33.52 MiB (sparse, cycle 7), 30.15 MiB (ring, cycle 19)
  and 33.22 MiB (hub, cycle 8). After that, the maximum of each 20-cycle
  interval is flat: about 31.1 MiB (sparse, hub) and 28.8–28.9 MiB (ring).
- **Steady state** over the last 100 cycles (frozen): mean 30.35 / 28.06 /
  30.35 MiB, minimum 27.37 / 25.15 / 27.37 MiB, maximum 31.10 / 28.86 /
  31.10 MiB (sparse / ring / hub).
- **Declared criterion** (max(151–300) ≤ max(31–150), and |slope 151–300| ≤
  1% of the early mean per 150 cycles):
  - **sparse: bounded.** Its later maximum is 134,472 B lower;
  - **ring and hub: NOT bounded by the declared criterion.** Their later
    maximum exceeds the earlier one by 9,384 B and 9,000 B (0.03%);
  - all three meet the slope part: +0.21% (ring), +0.10% (sparse, hub);
  - the per-interval maxima for ring drift from 28.764 to 28.854–28.858 MiB
    over 13 intervals (+0.31–0.33%). This diagnostic does not establish
    whether that drift continues or levels off.
  - presized variants (`summary.txt`): sparse is bounded in both; ring and hub
    are NOT bounded by the declared criterion in either. Their later maxima
    are the same bytes as the frozen build's, and their slopes are +0.02% to
    +0.13%.

## 2. Mitigation: pre-sizing

| | C3 late/early | C3 30-cycle growth (≤ 0.10) | C3 | Peak (300 cycles) | B5 lifecycle/plain (≤ 3×) |
|---|---|---|---|---|---|
| sparse frozen | 0.927 | +0.103 | FAIL | 33.52 MiB | 2.453 |
| sparse presized-compaction | 0.927 | +0.119 | FAIL | 33.52 MiB | 2.453 |
| sparse presized-start | 0.967 | −0.055 | PASS | 32.13 MiB | **3.395** |
| ring frozen | 0.950 | +0.172 | FAIL | 30.15 MiB | — |
| ring presized-compaction | 0.950 | +0.191 | FAIL | 30.15 MiB | — |
| ring presized-start | 0.998 | −0.014 | PASS | 28.86 MiB | — |
| hub frozen | 0.927 | +0.119 | FAIL | 33.22 MiB | 2.442 |
| hub presized-compaction | 0.927 | +0.135 | FAIL | 33.22 MiB | 2.442 |
| hub presized-start | 0.969 | −0.044 | PASS | 31.80 MiB | **3.403** |

(B5 is measured at 100k on sparse and hub only, as in the qualification.)

**presized-compaction**
- It does not change the first interval or the peak. It raises the
  steady-state minimum (27.37 → 29.49 MiB sparse/hub, 25.15 → 27.27 MiB
  ring) and lowers the later slope.
- C3 gets slightly worse (growth +0.119 / +0.191 / +0.135). The first
  compaction's rebuild now keeps the headroom, so the early-to-late ramp is
  steeper.

**presized-start**
- It moves the sawtooth headroom into construction. C3 then passes in all
  three topologies, and the peak drops by 1.29–1.42 MiB.
- The cost: the construction heap rises from 23.0 to 31.8 MiB (sparse) and
  from 22.5 to 31.3 MiB (hub). **B5 would then FAIL** (3.40× against 3×).

## What this establishes (no verdict)

- **The C3 FAILs** come from the first compaction interval: incremental
  growth of the catalog and engine tables, plus accumulated retired slots,
  before the first rebuild. Over 300 cycles, no growth beyond that peak was
  seen. Ring and hub miss the strict-maximum criterion by about 9 KB, and
  ring's per-interval maxima drift by about 0.3%. Whether growth stays
  bounded beyond 300 cycles is not established.
- **Over 300 cycles** the heap oscillates in a band under the first-interval
  peak. Ring and hub miss the declared strict-maximum criterion by about
  9 KB.
- **Pre-sizing trades C3 for B5.** None of the variants measured here passes
  both under the current rules. Any other pre-sizing policy (for example
  partial headroom) or a rule change is a decision for the maintainer.
