# D3b: B4 `ops` sparse 100k window, profiled by operation type and work (item 3, phase 2)

This diagnostic follows DIAGNOSTICS-PLAN-2.md, D3b. It is not part of the
qualification. The a3-3 result stands: INCONCLUSIVE +23.76% [+18.05, +26.72]
against a 25% tolerance. This measurement is separate from it.

## Setup

**What is replayed.**
- Each pair of the frozen probe builds fresh arms and applies the same
  deterministic trace, so the measured window replays exactly at core level
  with no HTTP. The harness is in `harness/`.
- **Lifecycle arm:** the frozen `ops` trace (sparse 100k, seed 5000001,
  40 requests; `connected` filtered out). It is applied to a
  `LifecycleGraph` built incrementally, as the probe's `standalone` server
  builds it.
- **Plain arm:** the frozen probe's planner (copied verbatim) turns the trace
  into legacy operations. They are applied to a plain `ConnectivityGraph`.
- The operation counts reproduce D3 exactly: 9,464 lifecycle and 13,057
  plain.

**Measurements.**
- **(a) Timing:** 24 whole-window replays per arm after 2 warmup,
  alternating arms, with a fresh graph each time.
  - The core is uninstrumented: the candidate e75ff6a, unchanged.
  - A separate pass reads the clock once per operation to give the time per
    type.
- **(b) Work counters:** an instrumented core (`d3b-counters.diff`, relaxed
  atomics). One replay per arm; the counts are deterministic.
- **(c) Profile:** macOS `sample` at 1 ms.
  - 6 windows per arm, alternating, each 10 s of repeated replays.
  - Only stacks under `replay_lifecycle` / `replay_plain` are counted:
    2,393 and 2,409 samples.
  - The whole-window and profile runs use the same binary. Its
    debug-info-only setting changes no code.
- **Supplementary, a departure from the plan.** The reference's planner
  over the same trace, timed (`planner` mode). The frozen probe runs it
  untimed. It was added because the counters showed that the lifecycle arm
  does this bookkeeping inside the window.

**Outputs.** In `raw/`, with binaries in `raw/binary-sha256.txt`. The
summaries are `summary.txt` (`summarize.py`) and `profile-summary.txt`
(`profile_summary.py`).

## (a) Whole window

| | Lifecycle | Plain | Difference | Ratio |
|---|---|---|---|---|
| Core replay (median of 24) | 1,354.8 µs | 541.2 µs | **+817.8 µs** (+553.8 to +1,133.0) | 2.537 (1.655–3.093) |
| D3 apply phase (server, for comparison) | 2,625.0 µs | 1,508.3 µs | +1,116.7 µs | 1.740 |

**The core replay accounts for 73% of D3's apply-phase difference**
(818 / 1,117 µs). The other ~300 µs is server-side handling per operation,
beyond the core. It costs about 134 ns per lifecycle operation against 74 ns
per plain operation in D3's apply phase, minus the core time here. It is not
profiled here.

## (b) Operation types and work (`summary.txt`)

| Type | Count | No-op | Time (µs, per-op pass) | ns/op | Engine link / cut | Engine elements shifted | Incident entries scanned | Neighbor catalog probes | Incident elements shifted | Incident binary searches |
|---|---|---|---|---|---|---|---|---|---|---|
| **Lifecycle arm** | | | | | | | | | | |
| set_node_active(false) | 1,509 | 8 | 484.4 | 321 | 0 / 5,895 | 11,397 | 5,960 | 5,936 | 0 | 0 |
| remove_node | 727 | 0 | 333.6 | 459 | 0 / 2,809 | 5,650 | 2,843 | 2,843 | 5,788 | 2,843 |
| link | 1,804 | 0 | 283.0 | 157 | 1,790 / 0 | 4,515 | 0 | 0 | 4,597 | 5,412 |
| set_edge_enabled(false) | 1,465 | 6 | 218.7 | 149 | 0 / 1,438 | 5,587 | 0 | 0 | 0 | 2,924 |
| set_edge_enabled(true) | 1,479 | **1,471** | 122.6 | 83 | 7 / 0 | 16 | 0 | 0 | 0 | 1,487 |
| cut | 334 | 0 | 59.3 | 178 | 0 / 328 | 1,284 | 0 | 0 | 1,313 | 668 |
| set_node_active(true) | 1,419 | **1,401** | 52.3 | 37 | 63 / 0 | 251 | 65 | 64 | 0 | 0 |
| add_node | 727 | 0 | 13.5 | 19 | — | — | — | — | — | — |
| **Total** | **9,464** | **2,886** | 1,568.5 | | **1,860 / 10,470** | 28,700 | 8,868 | 8,843 | 11,698 | 13,334 |
| **Plain arm** | | | | | | | | | | |
| cut | 10,470 | 0 | 445.2 | 43 | 0 / 10,470 | 32,244 | | | | |
| link | 1,860 | 0 | 91.7 | 49 | 1,860 / 0 | 4,727 | | | | |
| add_node | 727 | 727 | 12.1 | 17 | | | | | | |
| **Total** | **13,057** | 727 | 549.3 | | **1,860 / 10,470** | 36,971 | | | | |

How to read the table:
- **No compaction** occurs in the window in either arm.
- **The per-op pass adds clock overhead, unevenly:** +214 µs in the lifecycle
  arm and +8 µs in the plain arm against the whole-window replay. The
  per-type times are therefore approximate shares.

## (c) Profile (`profile-summary.txt`)

| Self-time attribution | Lifecycle | Plain |
|---|---|---|
| Engine (`Graph::link`/`cut` and their `memmove`) | 46.3% | 93.4% |
| Lifecycle catalog code (`set_node_active`, `set_edge_enabled`, `remove_node`, `link`, `Subject::apply`) | 34.6% | — |
| `memmove` and allocation under lifecycle catalog code (incident vector shifts, `affected` vectors) | 19.1% | — |
| Plain dispatch | — | 6.6% |

Converted with the whole-window medians:
- **Lifecycle:** engine about 627 µs, catalog and dispatch about 728 µs.
- **Plain:** engine about 505 µs, dispatch about 36 µs.

## What this demonstrates

1. **Operation count does not measure work** (the maintainer's correction
   holds).
   - Both arms make exactly the same engine changes: 1,860 links and 10,470
     cuts.
   - The lifecycle arm's 9,464 operations include 2,886 no-ops: flag
     re-sets, 37–83 ns each.
   - Its effective operations each carry several engine updates.
     `set_node_active(false)` averages 3.9 engine cuts; `remove_node`
     averages 3.9 cuts and 8 incident elements shifted.
2. **Engine work is equivalent; the difference is catalog bookkeeping.** The
   lifecycle arm also maintains the registered topology and flags:
   - 8,868 incident entries scanned;
   - 8,843 neighbor catalog probes;
   - 11,698 incident elements shifted;
   - 13,334 binary searches;
   - per-operation catalog lookups, and one `affected` vector per effective
     `set_node_active`.

   Profile attribution puts the catalog side at about 728 µs, roughly 89% of
   the +818 µs core difference.
3. **That bookkeeping is what the plain arm's application planner does
   outside the window.** The frozen B4 reference plans untimed. The planner
   keeps the same registered topology and flags in nested hash maps and
   costs **693.7 µs** (652.9–857.3, 24 replays) over the same trace.
   - At core level, lifecycle (1,355 µs) against plain plus planner
     (541 + 694 = 1,235 µs) is about **+10%**.
   - This is context, not a verdict. The planner's structure differs from
     the catalog, and the frozen B4 rule is not reinterpreted.
4. **Sites, classified:**

| Site | Class | Mechanism (unmeasured unless stated) |
|---|---|---|
| Engine `cut`/`link` and their `memmove` | **inherent**: the same in both arms | — |
| Neighbor scan and catalog probe per incidence in `set_node_active` (5,936 probes) and `remove_node` (2,843) | **inherent** to deriving effectiveness from the registered topology | The planner does the same scan. |
| Incident vector shifts on `link`/`cut`/`remove_node` (11,698 elements) | **implementation, plausible** | The sorted-`Vec` incident lists shift on insert and remove; another layout trades this against lookup cost. |
| `affected` vector allocation in `set_node_active` | **implementation, plausible** | A reused buffer or a small inline vector. All allocator frames together are about 4% of lifecycle samples, not all of them from `affected`. |
| About 300 µs of server-side handling per lifecycle operation beyond the core | **unclear** | Not profiled. Candidates are operation conversion and validation in the batch path. |

## Limits

- One run per measurement, on a laptop that was not gated.
- The core replay does not include the server's per-operation handling (see
  (a)).
- The profile's sampling interval and the inlining limit attribution. With
  LTO, some catalog helpers are inlined into the public methods.
