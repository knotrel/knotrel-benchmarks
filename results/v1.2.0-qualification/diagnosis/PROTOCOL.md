# knotrel#182 BFS regression diagnosis: protocol

Declared and committed **before** any diagnostic run. It was authorized by the maintainer on
2026-11-27 ("Diagnose BFS regression").

Constraints:
- Attempt 1 of #182 stays valid.
- Candidate 9faf168 stays not qualified.
- The frozen thresholds and classes are unchanged.
- No result here is a qualification verdict, and the full campaign is not repeated.

## Already established from preserved data (no new runs)

The V1 and K1 records split query time into `query_true` and `query_false`. The harness
source is identical in both arms: K1 uses benchmarks 4cf9b103 for both, V1 uses df635a1e for
both. Only the knotrel revision differs: v1.1.0 57c35e8 against 9faf168.

- **Hub and redundant-bridge workloads.** Connected queries are 15× to over 800× faster:
  the meeting point of the two searches is near both endpoints.
- **Chain, cycle, components and sustained-path workloads.** Both connected and
  disconnected queries are 1.3× to 3.1× slower.
- **Disconnected queries.** They are slower in every family, 1.02× to 2.25×.
- **`compact-workspace`.** Its source is unchanged: `workspace.rs` is not in the diff and
  `connected_with_workspace` is identical. Yet V1's chain-split-rejoin 10k cell is 1.11×
  slower, `query_true` 1.17× and `query_false` 1.03×. The same engine on sustained-path is
  1.00×.

## Hypotheses

- **H-work:** the bidirectional search examines more adjacency entries on these traces.
  - Disconnected queries: it explores both components, while the old search explores
    the source's component only.
  - Path-like graphs: both sides advance along the path.
- **H-const:** it examines about as many entries but pays more per entry. Candidate costs:
  - a second bitset test (`other.contains`);
  - the `pending` degree read of every newly marked vertex;
  - the frontier swap;
  - a second V-bit allocation.
- **H-layout** (`compact-workspace` only): the function's machine code is unchanged, and the
  difference comes from code placement in the harness binary built against a different
  `knotrel-core`.

## Diagnostics

### D1: work count (untimed, deterministic)

- **Traces.** Export with the attempt-1 candidate harness (`--trace-out`) for the frozen
  cell arguments (`--rounds 100`, seed 42): chain-split-rejoin, cycle-alternatives and
  components-join-split at 10k and 100k; sustained-churn-path and sustained-churn-blocks
  at 10k and 100k (`--rounds 20` for the V1 cell, 100 for K1 per the matrix).
- **Controls.** hub-alternatives 10k and redundant-bridge-churn 512.
- **Replay.** Both algorithms are reimplemented line for line from the two sources: v1.1.0
  `Graph::connected` (mark on enqueue, early exit on `neighbor == b`) and 9faf168
  (`Side::expand`, smaller `pending` side first).
- **Counts.** Per query: adjacency entries examined, vertices marked, allocations of V bits.
- **Validation.** Every replayed answer must equal the trace's `expected`. Otherwise D1 is
  void.

### D2: per-entry cost (from the preserved timings, no new timing)

For each cell and arm: c = median `query_*` total_ns / entries examined (D1).

### D3: machine code of `connected_with_workspace` (untimed)

Disassemble the function in `targets/A-B-harness` and `targets/A-C-harness` (the V1
binaries). Compare the instruction streams with addresses normalized, and the hot loop's
start address mod 64.

### D4: layout control (timed, small)

`--engine compact-workspace` on chain-split-rejoin 10k, `--rounds 100`, seed 42. It uses the
K1 binaries (`targets/base-harness` against `targets/cand-harness`), which are other builds
of the same unchanged function, and the V1 pair (`A-B` against `A-C`): 12 alternating pairs
each. Statistic: median `query_true` and `query_false` per arm.

## Decision rules (fixed now)

Per cell, compare the time ratio R (candidate over v1.1.0, from the attempt-1 medians) with
the work ratio W (D1):

- **H-work:** W ≥ 0.8·R, so work explains at least 80 % of the slowdown.
- **H-const:** W ≤ 1.2 and c_cand / c_v110 ≥ 1.5.
- **Mixed:** otherwise. Both factors are reported.

For `compact-workspace`:

- **H-layout supported:** D3 shows identical instructions, apart from addresses, and D4
  shows a ratio within [0.95, 1.05] on the K1 binaries while the V1 pair reproduces a
  ratio ≥ 1.07 on `query_true`.
- **H-layout rejected:** D3 shows different instructions. Then the code difference is
  located and reported.
- **Unresolved:** any other outcome.

## Budget

At most **30 minutes of host time** in all:
- D1: trace export plus Python replay, about 10 min;
- D3: seconds;
- D4: 4 × 12 runs of about 10 ms each, plus process start-up, under 2 min.

No other runs. Host conditions as in attempt 1: Docker stopped, `caffeinate`, swap
counters recorded.
