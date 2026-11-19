# v0.7.0 re-qualification: diagnostics phase 2 (declared before measuring)

Ordered by the maintainer on 2026-11-19 (path C, all items authorized together
with no further approval needed for these activities). The order, verbatim
points:
1. "profila `prepare`, separando parsing, validazione, catalogo e costruzione
   del grafo effettivo";
2. "sperimenta il pre-dimensionamento parziale e del solo catalogo",
   measuring C3, B5, peak memory and import cost together, and run beyond
   1,000 cycles for the ring drift;
3. "profila la finestra misurata e scomponi le operazioni per tipo e lavoro
   svolto";
4. "isola il costo del middleware e dichiara prima della raccolta numerosità
   e criterio di arresto della misura aggiuntiva";
5. fix the probe's 503/412 handling with bounded retries and backoff, record
   attempts, refusals, completions and overall latency, check that retry
   does not hide starvation, and freeze anew for future collections.

The stats/health admission control is not changed. A separate proposal is
prepared instead.

Two corrections from the maintainer apply to every reading below:
- fewer operations do not necessarily mean less work;
- L/F +13.7% compares arms that build different engines, so it does not by
  itself identify a removable cost.

## Rules (unchanged from phase 1)

- **a3-3 and its verdicts are preserved:** REGRESSION, FAIL ×3,
  INCONCLUSIVE ×2, INVALID. Nothing here re-runs, replaces or supersedes
  them. No exception, threshold change or release.
- **Product patches are diagnostic builds only**, in scratch checkouts, kept
  here as diffs. None is merged.
- **Host:** the developer laptop, not gated, disclosed as such. Timing runs
  never overlap a build or another timing run.
- **Every run is reported**, with the reason for any failed or discarded run.

## D1b: import `prepare` profile (item 1)

**Build.** A diagnostic build of candidate e75ff6a (`d1b-instrument.diff`).
It adds process-wide nanosecond accumulators at sub-phase boundaries of the
import worker, then reads them after each import. They cost one clock read
per boundary, about 20 per import.

**Sub-phases.**
- **Both servers:** parse (typed `parse_import_body`), request checks
  (instance and graph ID), and publish.
- **Lifecycle (L):**
  - spec conversion (wire to `NodeSpec`/`EdgeSpec`);
  - catalog: the node pass, the edge counting pass (self-loop and limit
    checks plus endpoint probes), incident allocation, the fill pass;
  - sort and dedup of incident lists, including conflict detection;
  - `finish` counts and shrink;
  - effective engine: ID sort and index assignment, adjacency allocation, the
    effective-edge pass, and `from_sorted_adjacency`.
- **Plain (F, E):** the `add_node` loop and the `link` loop, with per-link
  validation.

Validation is not a separate pass in L. The self-loop and limit checks sit
in the counting pass, and conflict detection in sort/dedup. Those sub-phases
are labelled as mixing validation with construction.

**Size.** 30 imports per arm (L, F, E) after 3 warmup rounds, in rotating
order, one fresh server per import. The same inputs as D1 (sparse 10k, seed
5000001, 60% inactive, 30% disabled).

**Reported.**
- The median per sub-phase, with the pair min–max.
- The sum of sub-phases against the measured import (coverage).
- For each L sub-phase, whether the full-topology contract requires it, or
  whether an alternative implementation could reduce it. Any "reducible"
  claim names the mechanism; none is claimed as proven without a measured
  variant.

## D2b: partial pre-sizing and a long run (item 2)

**Structural fact, stated before measuring.** The catalog and the engine ID
map are hashbrown tables, whose bucket counts are powers of two. At 100,000
nodes the table holds 131,072 buckets (capacity 114,688). Any reservation
above 114,688 entries gives 262,144 buckets. A "partial" factor such as 1.25n
therefore equals 2n for these tables. Partial sizing is meaningful only for
the adjacency header `Vec`, which is sized exactly, and by choosing which
component to pre-size.

**Variants** (count-alloc builds, start pre-size via the D2 hook, env-selected):

| Variant | Catalog | Engine ID map | Adjacency headers |
|---|---|---|---|
| frozen | — | — | — |
| cat | 2n | — | — |
| ids | — | 2n | — |
| hdr-1.25 / hdr-1.5 / hdr-2 | — | — | 1.25n / 1.5n / 2n |
| eng | — | 2n | 2n |
| full (D2's presized-start) | 2n | 2n | 2n |

**Measured per variant** (deterministic byte counts, one run each):
- C3 over 30 cycles: sparse, ring, hub;
- B5 at 100k: sparse, hub;
- peak and steady state over 300 cycles.

**Import cost.** The same component policy applied at the end of a bulk
import (`try_from_topology`). This is how a product mitigation would reach
the server's import path.
- Import time: in-process, 100k sparse, 24 pairs after 2 warmup, each
  variant paired and alternating with frozen, on a normal (non-count-alloc)
  release build.
- Post-import net heap: on the count-alloc build.

**Long run.** 1,500 cycles (50× the qualification), sparse, ring and hub,
on frozen and on any variant that passes both C3 and B5.

Declared criteria for the long run:
- **Bounded:** max(cycles 751–1500) ≤ max(cycles 31–750), and the
  least-squares slope over cycles 751–1500 is within ±1% of the early mean
  per 750 cycles.
- **Ring drift settled:** the maximum of the per-compaction-interval maxima
  over the last 25 intervals is at most the maximum over intervals 26–50.

The full per-interval maxima series is reported.

## D3b: window profile and per-type breakdown (item 3)

Each pair of the frozen probe builds fresh arms and applies the same
deterministic trace. The window can therefore be replayed at core level, with
no HTTP, as many times as needed.

**Harness.** `d3b-replay`:
- **Starting state:** the frozen `ops` scenario (sparse 100k, seed 5000001,
  40 requests), built as the probe's `standalone` builds it.
- **Lifecycle arm:** the 9,464 lifecycle operations in batches of 256.
- **Plain arm:** the planner's 13,057 operations.

**(a) Timing.** On the candidate core, uninstrumented.
- 24 replays per arm after 2 warmup, alternating arms, a fresh graph each
  replay (untimed).
- The whole-window time, uninstrumented, is compared with D3's apply phase
  ratio as a fidelity check.
- Per operation type, from a separate pass with a clock read per operation;
  that pass's overhead is disclosed.

**(b) Work counters.** A diagnostic core build (`d3b-counters.diff`) with
relaxed atomic counters, one replay per arm (deterministic). Per type:
- count, and no-op count;
- engine `link`/`cut` calls;
- adjacency elements shifted by `Vec::insert`/`remove`;
- incident entries scanned and incident elements shifted;
- catalog probes;
- compactions and the vertices they rebuild.

Engine `connected` is not in the trace.

**(c) Profile.** macOS `sample` at 1 ms.
- 6 windows per arm, alternating, each 10 s of repeated replays, on a
  debug-info build of the uninstrumented core.
- Only stacks under the replay function are counted.

Reported: the top self-time sites per arm, and the difference between arms.

**Reading.** Cost per operation type is set against the work per type
measured in (b), never against the operation count alone. A site is classed
as "inherent" (required by the lifecycle semantics: catalog and flags kept),
"implementation" (a cheaper implementation with the same semantics is
plausible) or "unclear". "Implementation" claims name the mechanism and are
not proven without a variant.

## D4b: middleware isolation and declared re-measurement (item 4)

**(a) Middleware alone.** A micro-measure of `track_http`'s own work per
request (label resolution, two `Family::get_or_create` calls, one counter
increment and one histogram observation), on the candidate:
- 1,000,000 iterations in a tight loop;
- median of 15 repetitions;
- times 37 requests per window.

**(b) Re-measurement by subtraction.** The frozen `metrics-ops` scenario
(sparse 10k, 40 requests, seed 5000001), metrics on against off in the same
process, as frozen.
- **V0:** the a3-3 candidate's frozen probe binary, unmodified (no D3
  counters).
- **V1:** a diagnostic build identical to V0 except that the `track_http`
  layer is not installed (`d4b-no-middleware.diff`). The handler and
  operation metrics are unchanged.
- **V2, conditional:** a build exporting exactly V0's metrics through a
  cheaper middleware path (pre-resolved per-route handles). It is built and
  measured only if (a) or V0 − V1 indicates a middleware share of at least
  1.0 percentage point of the window.

**Numerosity and stop criterion (declared).**
- Each variant: exactly 200 analyzed pairs, split into two runs of 100 pairs
  plus 4 warmup each.
- Runs in ABBA order (V0, V1, V1, V0; V2 appended as V2, V2 if run).
- Fixed sample size: no interim analysis, no early stop, no extension. A run
  that aborts on a probe error is reported and repeated once, with the reason
  stated. A second abort ends that variant as "not measured".
- n = 200 was chosen before collection from a3-3's interval width at n = 24
  (5.65 points). Width scales as 1/√n, so the target half-width is about 1
  point.

**Estimator.** The frozen method: per-pair log ratio, median, and a
distribution-free 95% order-statistic interval. For n = 200 the ranks are
[r(86), r(115)] (binomial, p = 0.5, two-sided 95%).

**Middleware share.** V0 − V1 overhead. A difference is claimed only if the
two intervals do not overlap. These numbers do not bear on the a3-3 verdict.

## D5b: probe 503/412 handling and a new tooling freeze (item 5)

**Change** (`tools/contention-probe`, for future collections only):
- **ETag refresh:** `GET /v1/stats`, retried on 503 or an I/O error. Backoff
  starts at 10 ms and doubles up to 160 ms per wait, for at most 12 attempts
  (at most about 1.2 s of waiting). Exhaustion is recorded as
  `refresh-exhausted`, never hidden.
- **On a 412:** one refresh and one retry of that import. A second 412 is
  recorded as `precondition-after-refresh`.
- **Records per configuration:**
  - stats attempts and 503 refusals;
  - refreshes, exhausted refreshes, and refresh latency (median and max);
  - imports attempted and completed, 412s, retries;
  - per-import total latency, including refresh and retry (median and max).

**Starvation check.** A starving configuration must not look successful:
- a configuration with any `refresh-exhausted`, any
  `precondition-after-refresh`, or completed < attempted is flagged
  `import_starved`;
- the refresh time is reported, so slow completion stays visible.

**Verification.**
- Unit tests against a stub server: 503 then 200; persistent 503 leading to
  exhaustion; 412 then refresh then 201; 412 after refresh.
- Runs on the D5 setup (candidate server, 100k, seed 7,
  `c16-events` → `c64-none` → `c64-import`):
  - 3 runs of the fixed probe;
  - 3 runs with the stored token made stale and the initial refresh skipped,
    as in a3-3, to show recovery through 412 → refresh.
- A starvation demonstration: a stub where stats is always 503, to show that
  the configuration is flagged and not counted as completed.

**Freeze.**
- PROTOCOL §11 "Amendment 4 (probe refresh, future collections)".
- The MATRIX and analyzer changes needed to carry `import_starved` into the
  validity rule.
- Tests, then an independent review, then `FREEZE-A4.json`. It is a tooling
  freeze for future collections; the candidate commit is set when the
  maintainer approves a campaign.
- a3-3 remains under FREEZE-A3 revision 2, and its row stays INVALID.

## Stats/health admission proposal (no product change)

`STATS-ADMISSION-PROPOSAL.md` sets out the options and the evidence each
would need, including the risk that admitting stats outside the bounded
permits worsens saturation:
- status quo with client guidance;
- a small separate permit pool;
- a lock-free cached snapshot;
- exempting health/ready only.

## Synthesis

`DIAGNOSTICS-PHASE2-SUMMARY.md`:
- demonstrated causes, kept distinct from hypotheses;
- interventions verified by a measured variant;
- quantitative trade-offs;
- a proposed qualification path.

An independent review precedes it. Items 5 and 7–10 stay pending.
