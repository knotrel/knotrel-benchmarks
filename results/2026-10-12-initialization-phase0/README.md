# Initialization Phase 0: instrumentation implemented, baseline gated

**Outcome: stopped after calibration.** The requested broad initialization
baseline is **not established**. No optimization was implemented. The timing
accounting and correctness tests pass, but HDT failed the predeclared measurement
stability gate. No sparse/cyclic/disconnected performance runs or configured-limit
comparisons were started, and no unfavorable observation was replaced.

## Implementation and boundaries

The new [initialization runner](../../crates/knotrel-benchmarks/src/bin/initialization-profile.rs)
uses existing generated workloads and graph constructors. The
[adapter](../../crates/knotrel-benchmarks/src/engines.rs) now shares its unchanged
construction operations between a no-clock constructor and an observed
constructor. Normal dynamic replay, its JSON schemas, and trace fingerprints
remain unchanged. The core worktree, algorithms, public core APIs, manifests,
lockfiles, and historical evidence were not changed.

The [methodology](../../docs/methodology.md#initialization-phase-diagnostic)
defines each interval:

- Contiguous **total initialization**: generation through a ready graph,
  including compact trace encoding/fingerprinting.
- **Setup**: the historical node-vector-through-initial-edge-loading boundary.
  The diagnostic additionally checks that each initial edge changed the graph.
- Separable setup phases: node-vector creation; adapter ID-map validation;
  empty-backend construction plus vertex registration; return/temporary-map
  cleanup; initial edge insertion; checked residual bookkeeping.
- Input generation includes the generator's inseparable validation/oracle work.
  No input file parsing is measured. Dynamic validation, when requested for
  tests, runs after the final timestamp.

All observed durations sum **exactly** to their corresponding enclosing
intervals. The largest residual bookkeeping interval was 0.1495% of setup.
Residual is not total clock overhead: clocks also perturb their adjacent phases.
No overhead was subtracted.

No attempt was made to independently time ID lookups, allocator activity,
connectivity classification, AVL links, or incidence-set updates inside the
edge loop. That would require more intrusive instrumentation. Root/rank/growth
counts from the design are likewise unavailable in this nonintrusive baseline;
initial edge dominance must not be relabeled "AVL dominance."

## Protocol and stopping decision

[Collector](../../scripts/run_initialization.py),
[raw manifest](calibration/manifest.json),
[analysis](calibration/analysis.json).

- One locked release binary, Rust 1.98.1, thin LTO, one codegen unit.
- Apple M4, 10 CPUs, 16 GiB RAM, macOS 27.0.1 arm64.
- Core `61a3556435f10ec9d5fe768682f1195ebd22ac71`;
  benchmark base `1567a4e2adee8f3e35eae9923107505868b3f01d` plus captured changes.
- Binary SHA-256:
  `9992c7104ac1b6875aebe1a18d024b266feae55f48d513dfc893b3e71fe99fc5`.
- Dense bridge: 512 vertices, 65,281 initial edges, seed 42, one generated
  round; identical ordered trace fingerprints across all arms.
- Six adjacent whole/phases pairs per backend, three AB/three BA, pair order
  shuffled with seed 42: **36 fresh processes**, one repetition, no warmup.
  No dynamic operations executed; no concurrent assistant builds or tests.
- The whole control disables internal phase clocks through the same source
  path, retaining setup and total timers. It is not a frozen historical binary.
- Predeclared gate: absolute median paired setup change <=5%; paired bootstrap
  95% interval within [-10%, +10%]; residual <1%. These are coarse-attribution
  thresholds, not a sub-percent no-overhead certification.

Paired changes are `100 * (phases / whole - 1)`. Intervals use 5,000 seeded
resamples of the six process pairs; this small sample is exploratory.

| Backend | Median paired change | Bootstrap 95% interval | Gate |
| --- | ---: | ---: | --- |
| BFS | +0.35% | [-4.62%, +3.24%] | Pass |
| ETT | -0.70% | [-5.34%, +4.54%] | Pass |
| HDT | -1.71% | [-4.28%, +10.49%] | **Fail** |

The HDT adverse pair is preserved:
[phase run](calibration/000-hdt-1-adapter-phases.json) 10.373500 ms setup versus
[whole run](calibration/001-hdt-1-adapter-whole.json) 8.645834 ms, **+19.98%**.
The other five HDT changes were -2.69%, +1.01%, -5.27%, -0.74%, and -3.30%.
This does not prove a 19.98% instrumentation tax: scheduling, allocator/cache
state, frequency and code-layout effects remain confounded. Host load averages
were 6.75 before and 6.61 after on a shared 10-CPU host; these observations do
not establish the cause of the outlier.

All processes exited successfully. The collector deliberately returned failure
**after preserving all records** because the statistical gate failed. The
planned 72-process topology baseline and 36-process facade comparison were not
launched. Thresholds were not relaxed and there were no retries.

## Descriptive calibration results only

The following are **not** a validated multi-topology baseline. They describe the
six phase-instrumented dense runs per engine; distributions, individual runs,
whole controls, and all phase quartiles remain in the linked analysis.
Medians of separate phases need not add to the median total.

| Backend | Setup median [Q1, Q3], ms | Setup min-max, ms | Total initialization median, ms | Peak process RSS median, MiB |
| --- | ---: | ---: | ---: | ---: |
| BFS | 1.365 [1.331, 1.392] | 1.293-1.422 | 2.496 | 5.20 |
| ETT | 5.154 [5.095, 5.197] | 5.007-5.452 | 6.347 | 16.41 |
| HDT | 6.999 [6.865, 7.635] | 6.531-10.374 | 8.165 | 32.52 |

Median phase durations in microseconds:

| Phase | BFS | ETT | HDT |
| --- | ---: | ---: | ---: |
| Input generation | 129.65 | 133.73 | 127.92 |
| Trace encoding/fingerprinting/disposal | 1,022.00 | 1,041.73 | 1,091.19 |
| Node vector | 0.23 | 0.33 | 0.44 |
| Adapter map/validation | 4.38 | 4.15 | 5.71 |
| Backend creation + vertex registration | 11.02 | 18.15 | 25.79 |
| Constructor return/map cleanup | 1.35 | 1.48 | 1.48 |
| Initial edge insertion | 1,343.21 | 5,088.54 | 6,952.33 |
| Residual setup bookkeeping | 1.33 | 1.58 | 1.81 |

For this dense input, **edge insertion is the clearly largest setup interval**
in every observed run: median shares BFS 98.64%, ETT 99.50%, HDT 99.47%;
minimum observed shares 98.15%, 98.08%, 97.99%, respectively. This large
separation supports a coarse descriptive observation despite the failed
stability gate. It does not establish a reproducible speedup or a particular
inner bottleneck. Sub-microsecond node-vector differences are too small for
useful attribution; do not compare them as backend speed differences.

Peak RSS is reported by macOS `/usr/bin/time -l`: fresh **build-only entire
child process**, including input/JSON buffers, allocator/runtime and reporting.
There is no dynamic replay or warmup high-water contamination. RSS is still
not ready-graph heap or phase-specific allocation; no peak subtraction is used.
Observed phase-run RSS ranges were 5.20-5.22, 16.41-16.45, and 32.50-32.56 MiB.
Historical setup numbers use different builds/OS/boundaries and are not a
before/after speedup comparison.

## Recommendation and acceptance criteria

**Do not begin a production optimization on this evidence alone.** First
establish the already implemented baseline on a quieter/exclusive host in a
new result directory, under a prospectively declared protocol. Any future
replication must retain this failed calibration; do not pool away its outlier.
No additional collection is performed in this task.

The strongest present directional evidence favors investigating the **initial
edge insertion path**, not adapter-map removal or vertex registration alone.
For this dense case, completely eliminating the latter phases would not reach
the design's 5% setup target. Shared indexed-edge insertion with fewer repeated
endpoint lookups remains a sensible *small candidate* once the baseline passes;
bounded reservation may help edge-phase growth, but that saving is unmeasured.
There is insufficient evidence to choose DSU classification, direct tour
construction, BFS append/sort, or a replacement library over that candidate.
Sparse tree results are essential before prioritizing direct forest building.
Trace JSON preparation is material to end-to-end harness initialization but
removing it would be a harness change, not a faster graph algorithm.

Acceptance for the next step:

1. Pass the unchanged coarse calibration gate; preserve all raw pairs, require
   exact timing accounting, identical trace identities, and no overlap with
   builds/tests. Do not treat a wide confidence interval as equivalence.
2. Complete the four-topology BFS/ETT/HDT baseline and default/configured facade
   comparison before claiming cross-workload priority. Keep build-only RSS and
   dynamic continuation measurements separate.
3. For a later Phase-1 candidate, retain ordered incremental semantics and all
   differential/invariant tests. Preselect the target cell; require >=5%
   median total-core-setup improvement and paired 95% CI below zero in the
   design's confirmation stage. Investigate dynamic regressions; reject a
   confirmed >5% slowdown or >10% fresh build-only RSS increase in controls.
4. Do not attribute an improvement to fewer allocations or AVL traversals
   unless those mechanisms receive separate valid evidence.

## Validation and preservation

- 38 benchmark Rust tests passed, including constructor parity across every
  existing adapter, timing accounting, unchanged trace identity, and dynamic
  oracle continuations across all four topologies and all three core engines.
- Three collector tests passed: balanced deterministic schedule, statistical
  handling, and rejection of inconsistent accounting.
- Formatting, Clippy `-D warnings`, and Rustdoc `-D warnings` passed.
- Verified all 82 recorded calibration artifact hashes and all 36 successful
  child exits. Existing output schemas and production sources remain unchanged.
- No commit or push. Implementation is available; Phase-0 performance baseline
  remains blocked by the calibration result, explicitly rather than silently.
