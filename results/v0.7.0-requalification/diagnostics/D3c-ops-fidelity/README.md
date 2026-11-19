# D3c: B4 `ops` sparse 100k fidelity on one binary, planner in the window (item 2, phase 3)

This diagnostic follows DIAGNOSTICS-PLAN-3.md, D3c. It is not part of the
qualification. The a3-3 result stands: INCONCLUSIVE +23.76%.

**Setup.**
- **One binary, one process, one workload.** The harness (`harness/`) links
  the candidate server, instrumented with one clock pair around each
  `state.apply` in the batch loop (`d3c-instrument.diff`). The workload is
  the frozen `ops` trace (sparse 100k, seed 5000001, 40 requests), with the
  frozen planner.
- **Arms**, per pair, in a rotating order:
  - **L:** lifecycle server window;
  - **P:** plain server window with planning untimed (the frozen reference);
  - **PP:** plain server window with the planning of each 256-op chunk timed
    inside the window;
  - **core-L and core-P:** core replays with the same per-call clock pair.
- **Run:** 24 analyzed pairs after 2 warmup, in the quiet phase-3 timing
  chain (`../PHASE3-TIMING-RUNS.txt`).
- **Outputs:** `raw/d3c.jsonl`. `summary.txt` comes from `summarize.py`.

## Results (`summary.txt`, medians)

| Arm | Window | Apply phase | In-call | Handling (apply − in-call) | Planning in window |
|---|---|---|---|---|---|
| L | 3,989.2 µs | 2,205.7 | 1,989.4 | 215.6 | — |
| P | 3,093.7 µs | 1,053.0 | 739.1 | 313.0 | (untimed) |
| PP | 5,056.1 µs | 1,818.6 | 1,516.2 | 302.1 | 1,163.7 |
| core-L, per call | 1,506.7 µs | | | | |
| core-P, per call | 512.0 µs | | | | |

**Fidelity check (declared).**
- **Check 1: FAILS.** The core per-call totals are 24.3% (L) and 30.7% (P)
  below the server's in-call totals. The declared bound was ±10%.
  `state.apply` in the server includes per-operation conversion and outcome
  construction that a core call does not.
- **Check 2: passes, but it is uninformative.** apply − in-call is handling
  by construction, so the residual is 0 whatever the data. This check was
  designed wrongly and is disclosed as such.
- **Fidelity: NOT RESTORED.** As declared, the core-level attributions (the
  D3b profile shares, the core replay ratios and the +10% figure) are
  withdrawn from the protocol argument. Only server-level measurements are
  used.

**Descriptive ratios at server level** (frozen estimator, n = 24, [r(7), r(18)]):
- **L/P** (frozen reference, planning untimed): **+30.08%** [+23.13%,
  +36.56%], pair range +8.0% to +81.7%.
- **L/PP** (planner in the window): **−21.25%** [−27.22%, −14.53%], pair
  range −42.1% to +8.0%.

## What this shows (no verdict)

- **The server-level comparison does not depend on the core replay.** With
  the planner's work inside the reference window, the lifecycle server's
  window is about 21% shorter than plain plus planner, on this host and
  this run.
- **The planner's work** is about 1.16 ms per window, close to D3b's
  separate measurement (0.69 ms core-only, without the server around it).
  PP's in-call time is also higher than P's: 1,516 against 739 µs.
  - That is plausibly cache interference from planning inside the window,
    which is part of what an application offering the same service pays.
  - It is not attributed further.
- **These figures come from one ungated run.** The equivalent cell is
  evaluated only in qualification 3, with the frozen estimator and its
  conformance rules. The L/P interval here (+23 to +37%) differs from
  a3-3's (+18 to +27%): host conditions differ.
