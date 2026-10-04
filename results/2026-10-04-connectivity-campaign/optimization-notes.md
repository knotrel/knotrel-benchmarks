# Runtime conclusions and optimization candidates

These are hypotheses grounded in this checkout and campaign, not measured
improvements. See [all runtime percentages](runtime-percentages.md). No backend
implementation or default was changed as part of this analysis.

## Does one backend win?

No. With each non-repeat scenario/cache-regime cell weighted equally, compact
and petgraph each win 17/62 (27.4%), ETT 15/62 (24.2%), HDT 13/62 (21.0%).
There are no exact median ties. In 56/62 cells, the winner's largest observed
runtime is below every other engine's smallest observed runtime. This range
check is not a significance test, especially with only two synthetic trials.
The six remaining winners should be treated as particularly tentative.

Sparse cells: petgraph wins 17/36, ETT 13/36, compact 5/36, HDT 1/36. Dense cells:
compact and HDT each win 12/24. ETT wins both fresh/warmed Cogentco cells, but
those are two regimes of one topology/seed, not two independent real datasets.
The repeated-query supplement has two ETT and two HDT wins, kept separate.

Equal scenario weight is a reporting convention, not a production workload
model. Changing sizes, ratios, memory constraints, startup costs or scenario
weights can change the ranking. Summing all runtimes would overweight the slowest
traces; averaging percentage improvements would hide tail regressions. Neither
is used to declare a champion. Counting all three Knotrel variants as one winner
would give a hypothetical per-workload selector an unfair advantage over a single
external baseline; we do not present that as product performance.

## Percentage examples (warmed median replay runtime)

| Scenario | Knotrel compact | Knotrel ETT | Knotrel HDT | External petgraph |
| --- | ---: | ---: | ---: | ---: |
| Path, 100k, 10% queries | baseline | +223.5% | +354.1% | -25.8% |
| Path, 100k, 90% queries | baseline | -91.8% | -90.6% | -15.7% |
| Cyclic blocks, 100k, 90% queries | baseline | -83.9% | +1276.1% | +67.5% |
| Dense single bridge, 512, 90% queries | baseline | +124.2% | -49.5% | +908.5% |
| Cogentco | baseline | -67.4% | -50.4% | -31.4% |

Here negative means **less runtime than compact**, positive more runtime. The
per-scenario tables separately use the **fastest engine** as baseline. Their
percentages differ because the denominator differs. These are replay wall times,
not query-only latencies and not the earlier sum of operation intervals.

## Candidate improvements, with acceptance gates

1. **Compact BFS: reduce scratch allocation/initialization.**
   `Graph::connected` in `knotrel-core/src/lib.rs` allocates a visited vector sized
   to all registered vertices and a new queue on every non-reflexive query.
   Investigate an optional caller-owned or per-worker traversal workspace,
   retaining the existing lock-free shared-query contract. Compare touched-entry
   reset versus generation stamps; stamps cost more memory and need safe rollover.
   Do not turn temporary traversal state into an unvalidated cached answer. The
   benchmark-only `dense-bfs` and petgraph already reuse scratch, but their other
   differences mean existing timings do not isolate the benefit of this change.
   Acceptance: allocations/query and setup/steady-state time, same graph and
   algorithm before/after, unknown-ID semantics, graph growth, successive mutations
   and concurrent callers. Check large fragmented graphs and memory usage too.

2. **HDT: profile replacement and promotion costs before changing the algorithm.**
   `hdt.rs::replace` and `promote` maintain incidence, sparse level state and Euler
   tours. The costly cyclic-block case records substantial tree promotions;
   counts do not tell us whether allocation, map lookup, tree edits or enumeration
   dominates time. Use diagnostic allocation/CPU profiles separate from normal
   measurements, then target the measured hotspot (for example storage locality
   or repeated bookkeeping). Preserve level/nesting invariants and amortized
   guarantees; skipping necessary promotions is not an optimization.
   Acceptance: lower cut totals and p95/p99 on cyclic blocks without materially
   regressing dense controls, correctness, or peak memory. Retain unchanged traces
   and fresh/warmed/repeat splits across before/after runs.

3. **ETT: reduce candidate-search and storage costs.**
   `dynamic.rs` already scans candidate-bearing vertices of the smaller component;
   do not propose that existing optimization as new. Its dense replacement scans
   remain expensive. Profile non-tree incidence visits and memory locality, then
   evaluate candidate indexing or compact storage with explicit update/memory
   costs. Dense workloads must remain a counterexample until measurements improve.
   Acceptance: cut tails and RSS, not merely connected-query p50, plus exact
   replacement behavior after repeated deletions and repairs.

4. **Keep the external baseline competitive and identifiable.**
   Petgraph already reuses traversal space. Preserve its exact pinned version and
   semantics; audit adapter overhead symmetrically for all engines. Any optimized
   alternative adapter should be a separately named variant, with original results
   preserved, rather than silently changing what “petgraph” denotes.

Recommended sequence: first a narrow compact-workspace experiment because it
can benefit the current default; in parallel planning, prepare the HDT cut profile
that targets the largest observed regression. Expand seeds, longer mixed updates
and real topologies before considering a backend policy. An adaptive selector
would need selection/switching/rebuild cost, memory limits and an independent
holdout evaluation; knowing each benchmark's winner in advance is not deployable
selection logic. No such selector is implemented or promised by these results.
