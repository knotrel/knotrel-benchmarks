# v0.7.0: phase-3 verifications before a new qualification (declared before measuring)

The maintainer decided the following on 2026-11-19, with no further
intermediate approval needed for these activities:

1. **Import.** The contract keeps the complete registered topology.
   - A future reference must be equivalent in capability, validation and
     guarantees.
   - L/E stays as a descriptive comparison of the extra cost.
   - No API change now.
2. **Ops.** The future reference window includes the planner work needed to
   offer the same service. Before that, the fidelity check is restored, with
   both arms measured on coherent builds, the same workload and paired
   collection. The current +10% stays indicative.
3. **C3.**
   - The catalog pre-size that passed B5 by 8 bytes is discarded.
   - Tombstone handling that avoids unnecessary growth is to be tried, with
     feasibility, peak memory and compaction latency checked.
   - The C3 window is not moved: both the transient and the steady state are
     measured.
   - The ring drift is to be classified as bounded or cumulative.
4. **Metrics.** Clock and counters are isolated on the same binary, with the
   protocol and the stop criterion declared first. The budget stays 6%.
5. **Probe.**
   - The correction is kept. An overall time budget consistent with the
     workload is added, with backoff and an attempt limit.
   - Budget exhaustion and incomplete imports stay visible.
   - The limit is not raised just to get a success.
   - The `ETag` on 412 is evaluated separately, for concurrency and
     semantics.

**Then:**
- the updated protocol, with the equivalence of the references argued and
  the current percentage thresholds kept;
- a3-3 and its verdicts preserved in full;
- after these targeted verifications, the candidate is prepared and the new
  qualification started;
- no release without a conforming qualification.

## Rules

- Nothing here changes an a3-3 verdict, a threshold or a rule of a3-3.
- Diagnostic product patches stay in scratch checkouts, archived as diffs.
  Only a change that meets its declared criterion below goes into the
  candidate.
- Every run is reported. Fixed sample sizes: no interim analysis, no early
  stop, no extension. A run that aborts on a probe error is repeated once and
  reported. An invocation error before any pair is reported and does not
  count as a run.
- The developer laptop, not gated. Timing runs never overlap a build or
  another timing run.

## D2c: tombstone handling (item 3)

**Mechanism under test.**
- The catalog (`FxHashMap<NodeId, NodeRecord>`) grows from 131,072 to 262,144
  buckets at cycle 5 because removals leave tombstones. `capacity()` reports
  live entries plus the growth headroom, and falls from 114,688 to about
  102,200 before the growth (D2b).
- **T1, rebuild instead of grow.** Before inserting a new key, if the insert
  would grow the table (`capacity() == len()`) and live entries are at most
  90% of the table's full capacity (the highest `capacity()` seen right after
  a rebuild or growth), the catalog is rebuilt into a fresh table sized for
  `len()`. That is the same bucket count, with no tombstones; entries move,
  incident vectors are not copied. Otherwise it grows as today.
- **T2:** T1, plus the same rebuild after each engine compaction when live
  entries are at most 90% of the full capacity.

**Builds.** One diagnostic core build (`d2c-core.diff`) with the policy
selected by an environment variable (frozen, T1, T2).
- A count-alloc probe build gives the bytes.
- A plain release build gives the latency. It times each catalog rebuild and
  each engine compaction with one clock pair per event.

**Measured** (fresh-ID churn of 5% per cycle, 100k, seed 5000001, sparse,
ring and hub):
- C3 over 30 cycles;
- B5 at 100k;
- peak, transient (first interval) and steady state;
- the number of rebuilds and compactions, and the duration of each (median
  and max, from the timing build).

**Long run.** 6,000 cycles (300 compaction intervals) for frozen, T1 and T2,
in all three topologies.

**Ring-drift classification (declared).** It uses the per-interval maxima of
net heap over intervals 151–300, and the least-squares slope with its 95%
interval (t-distribution, n − 2 degrees of freedom). Serial correlation is
not modelled; that is disclosed.
- **cumulative:** the lower bound is above 0;
- **bounded:** the interval includes 0, or lies entirely below 0;
- the same rule over intervals 2–150 is reported for comparison.
- The checkpoint counts (`catalog_node_capacity`, `incident_capacity`, engine
  vertices) at each interval maximum are reported to attribute any drift.

**Criterion to include T1 or T2 in the candidate.** All must hold:
1. C3 PASS in all three topologies, by the frozen rule;
2. B5 lifecycle/plain ≤ frozen's value plus 0.01×. Construction is not
   changed, so equality is expected;
3. the peak over 6,000 cycles is ≤ frozen's in every topology;
4. the maximum catalog-rebuild duration is ≤ the maximum engine-compaction
   duration measured in the same run. A rebuild must not introduce a stall
   longer than the one already accepted;
5. knotrel's own tests, Clippy and Rustdoc pass with the change and with new
   unit tests for it.

If both qualify, the simpler (T1) is chosen unless T2 is needed for criterion
1. If neither qualifies, the candidate keeps the frozen catalog, and C3 is
expected to FAIL again.

## D3c: ops fidelity, coherent builds, planner in the window (item 2)

**One binary, one process, one workload:**
- the candidate server with an instrumented batch path (`d3c-instrument.diff`);
- a core replay of the same operations;
- the frozen `ops` trace (sparse 100k, seed 5000001, 40 requests);
- the frozen planner.

**Instrumentation.** In the server's batch loop, one clock pair around each
graph call (`state.apply`). That separates **in-call** time from **handling**
time inside the apply phase. Window total and apply phase are recorded as in
D3.

**Pairs.** 24 analyzed pairs after 2 warmup. Each pair runs, in alternating
order:
- **L:** the lifecycle server window;
- **P:** the plain server window, with the planner untimed (the frozen
  reference);
- **PP:** the plain server window with the planner's planning of each chunk
  timed inside the window, before the chunk's requests (the future
  reference);
- **core-L and core-P:** core replays with the same per-call clock pair.

**Fidelity check (declared).**
- For each arm, the core replay's per-call total must be within ±10% of the
  server's in-call total, as medians over the pairs.
- The apply-phase difference L − P must equal (in-call difference) +
  (handling difference) within 10% of the apply difference. Anything left is
  reported as unexplained.
- If fidelity fails, the core-level attributions (D3b) are withdrawn from the
  protocol argument, and only server-level measurements are used.

**Reported, descriptive, no verdict:**
- L/P and L/PP: medians and pair min–max;
- the frozen estimator's 95% interval at n = 24 ([r(7), r(18)]).

The future cell is evaluated only in the new campaign.

## D4c: metrics clock and counters on the same binary (item 4)

**One diagnostic build** (`d4c-variants.diff`), with the variant selected by
`KNOTREL_D4C`:

| Variant | Metrics on, minus |
|---|---|
| `ctl` | nothing: the released code path, as the same-binary control |
| `nocount` | per-operation counters (`count_operation`) |
| `noclock` | the job clock: queue, lock-wait and execution histograms |
| `nogauge` | graph count gauges published after each state-changing job |
| `notrack` | the `track_http` layer |
| `noall` | all four |

Every variant except `ctl` reduces observability. Those variants locate cost
only.

**Workload and estimator.** The frozen `metrics-ops` scenario (sparse 10k, 40
requests, seed 5000001): metrics on against off in the same process, as
frozen. Per pair, ln(on/off); median and a distribution-free 95% interval.

**Numerosity and stop.**
- 200 analyzed pairs per variant: two runs of 100 plus 4 warmup.
- Order: ctl, nocount, noclock, nogauge, notrack, noall, then the reverse.
- Fixed n.

**A component's share** is ctl minus that variant. It is claimed only if the
two intervals do not overlap.

**Follow-up (declared, strict reading).** Only for a component whose share is
claimed:
- a same-observability variant is built (for example batch-local counter
  accumulation flushed once per batch, exporting identical series, checked by
  scraping);
- it is measured with the same protocol, against ctl;
- it goes into the candidate only if its interval does not overlap ctl's and
  every exported series is identical.

The 6% budget is not changed.

## Probe revision 4: overall time budget (item 5)

**Rationale from the workload.** The background import runs one import per
second, start to start, over a 5 s window. A refresh that cannot finish
within one import period has stalled the background activity. That is
starvation by definition, not a slow success.

**Rules.**
- The refresh deadline is **1,000 ms** from its first request.
- Backoff is 10, 20, 40, 80, then 160 ms per wait.
- At most **10** attempts. The cumulative backoff before the tenth attempt
  is 950 ms, so both limits are consistent.
- Each request's read timeout is set to the remaining budget.
- Exhaustion is recorded with its reason, `deadline` or `attempts`.
  Exhaustion and incomplete imports keep making `import_starved` true.
- The one retry after a 412 is unchanged.

**Disclosed before re-running.** With this budget, D5b's forced run 3 (an
11-attempt, 1.2 s refresh) would have counted as starved. The budget is
derived from the workload, not from that run.

**Verification.**
- Rust stub tests for the deadline, the attempt cap and the read timeout.
- The D5b live runs repeated, 3 fixed and 3 forced, with outcomes reported as
  they fall.

## ETag on 412: separate evaluation (item 5)

A diagnostic server build adds the current `ETag` to 412 responses of
replacement imports. Assessed:
- **consistency:** the token is read under the same write lock as the failed
  precondition check, so it equals the state that refused the request (a
  test checks this);
- **races:** the token can be stale as soon as the lock is released, as a
  `/v1/stats` token can (a concurrent-events test checks this);
- **semantics:** whether returning the token invites blind retries that
  defeat the precondition's purpose (lost-update protection), given
  single-feeder lease fencing.

The evaluation is a document plus tests in the diagnostic build. It is not
put into the candidate without a maintainer decision.

## New protocol (prepared before any collection)

`results/v0.7.0-qualification-3/`:
- thresholds unchanged;
- a3-3 referenced, not modified;
- capability-equivalent references for B4 `import-high` and B4 `ops`, with
  the equivalence argued, and the frozen L/E and L/P cells kept as
  descriptive;
- probe revision 4;
- conformance rules inherited from amendment 3 revision 2 unless stated.

It is reviewed and frozen before the maintainer launches the collection.

## Addendum 1 (declared 2026-11-19, before the measurements it names)

These follow the maintainer's message of 2026-11-19, which asks for the
running chain to complete first and sets these prerequisites for the
qualification 3 freeze:
- equivalent references with the same guarantees, including validation,
  catalog update and publication in the timed window; connectivity
  agreement alone does not show equivalence;
- previous seeds and workloads kept where possible;
- deterministic memory results kept apart from timings;
- the product T1 shown to reproduce the diagnostic variant without
  instrumentation;
- T1 adopted only after the chain, considering the transient peak,
  rebuild and compaction latency, and the impact on operations.

**A1. Timings only from the quiet chain.**
- D2c's rebuild and compaction latencies come only from the timing build in
  the phase-3 timing chain (`PHASE3-TIMING-RUNS.txt`). The count-build event
  durations were recorded while other runs and builds were active. They are
  reported as unreliable and are not used for criterion 4.
- Any activity that overlapped the chain is disclosed.

**A2. Impact of T1 on operations.**
- Cells: the two frozen B1 fresh-churn cells (`B1-ops-compact-bfs-sparse-
  {1000,10000}-fresh-churn`: `pairs --exp ops --mix fresh-churn`, 12 pairs
  after 2 warmup, seed 5000001). The windows are those a3-3 ran after the
  window multipliers: 16,000 for 1k (factor 2) and 48,000 for 10k (factor 1).
  This was corrected before running; the first text gave the unmultiplied
  8,000.
- Build: the D2c timing build, with policy frozen or T1 (`KNOTREL_D2C`) on
  the same binary.
- Runs: two runs per policy and cell, in the order frozen, T1, T1, frozen,
  after the phase-3 timing chain, on a quiet machine.
- Reported: the lifecycle arm's window and the cell ratio against its
  reference arm, per policy (medians, pair min–max). It is descriptive.
- Decision input: T1 is not adopted if it makes the lifecycle arm slower by
  more than the B1 tolerance (25%) by median in either cell.

**A3. Product T1 reproduces the diagnostic.**
- The frozen probes are built, count-alloc, against the candidate source
  with the product change (no diagnostic code).
- They run C3 (30 cycles) and B5 in all topologies, and 6,000 cycles in
  ring, sparse and hub.
- Every checkpoint's `net_heap_bytes` and logical counts must equal D2c's T1
  series byte for byte. With `stats_alloc` (the frozen probe) against `cap`
  (D2c), net live bytes are counted the same, as shown by the frozen-policy
  reproduction.
- Any difference stops the adoption of T1 until it is explained.

**A4. Equivalence checks of the equivalent references** (probe tooling,
before the freeze):
- **ops, ops-query:** inside the reference window, the application computes
  each lifecycle operation's outcome from its planner state, as the
  lifecycle server reports it per operation: changed or unchanged, or the
  error code (`self_loop`, `unknown_node`, `unknown_edge`). The plan then
  updates the catalog; publication is the plain server request.
  - After the window, every outcome must equal the candidate arm's per-item
    result. For `connected`, the answer is compared only where the
    application answers locally; forwarded queries are compared through the
    existing connectivity check.
- **events:** correction made before implementing. Contrary to what this
  item first said, the lifecycle feeder reports no per-event results, only
  `events_applied` and the state version (`FeederEventsResponse`). So there
  is no per-event outcome to reproduce, and the final-state check below
  applies.
- **All four, final state after the window:**
  - the candidate's `/v1/stats` lifecycle counts (registered nodes and
    edges, active nodes, enabled and effective edges) must equal the
    application catalog's;
  - the plain server's node and edge counts must equal the registered nodes
    and the effective edges.
- Any mismatch aborts the probe, which is a failed child.
- Each scenario is smoke-run at the cells' sizes (10k, 100k) before the
  freeze. Those runs are checks, not measurements, and their timings are not
  used.

**A5. Seeds.** Qualification 3 keeps a3-3's A session and extension seeds
(130720–130722, 130730–130732), reverting the draft's 2307xx. Every other
seed and workload is unchanged too. The equivalent cells reuse their frozen
counterparts' workloads, seeds and request counts.
