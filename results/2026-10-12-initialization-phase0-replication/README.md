# Phase 0 replication: calibration failed; baseline remains blocked

**Decision:** stop before the broad baseline or any optimization. Phase-0
instrumentation is implemented and validated, but this independent replication
does not establish the requested trustworthy multi-topology performance baseline.

The [first attempt](../2026-10-12-initialization-phase0/README.md) remains
unchanged. Its HDT calibration failed. This renewed request authorized one
complete independent replication under the [predeclared protocol](protocol.md),
not replacement of an adverse pair. The attempts are reported separately, not
pooled or selectively filtered.

## Implementation and validation

The existing [initialization runner](../../crates/knotrel-benchmarks/src/bin/initialization-profile.rs)
and [collector](../../scripts/run_initialization.py) required no further changes.
Before collection, all Rust build-input hashes and the three collector/helper
scripts were verified identical to the first, tested implementation.
Production core remains clean; graph algorithms, public core APIs, dependencies,
and normal dynamic-replay outputs remain unchanged.

The [methodology](../../docs/methodology.md#initialization-phase-diagnostic)
defines the separate input-generation, JSON/fingerprint, node-vector,
adapter-validation, registration, constructor-cleanup, edge-insertion and
residual intervals. Total initialization is a contiguous generation-to-ready
graph interval; setup retains the narrower node-vector-to-loaded-graph boundary.
All timestamps precede dynamic operations.

All 18 phase-instrumented records satisfy exact setup and total accounting.
The largest setup residual was **0.1421%**. Residual is only bookkeeping gaps,
not total clock overhead; exact accounting cannot prove non-perturbation.
Generator validation remains inside generation; backend creation is included
with registration. ID lookup, allocation, root traversal, AVL construction and
incidence maintenance remain inseparable inside the edge interval.
No fictional measurements of those inner costs are reported.

The previous implementation validation remains applicable because sources are
identical: 38 Rust tests, three collector tests, formatting, Clippy with warnings
denied, and Rustdoc with warnings denied passed. No code was changed or tests
run concurrently with this collection.

## Calibration evidence

[Raw manifest](calibration/manifest.json) and
[full distributions / paired observations](calibration/analysis.json).

- Apple M4, 10 CPUs, 16 GiB RAM, macOS 27.0.1 arm64, Rust 1.98.1 release.
- Same binary as the first attempt, SHA-256
  `9992c7104ac1b6875aebe1a18d024b266feae55f48d513dfc893b3e71fe99fc5`.
- 512-vertex dense bridge, 65,281 edges, seed 42, one generated round.
- Six adjacent whole/phases pairs per backend, balanced three AB/three BA;
  seeded pair order, **36 fresh processes**, no warmup or dynamic replay.
- All processes completed successfully and graph/trace identities matched.
- Unchanged gate: absolute median paired setup difference <=5%; exploratory
  paired bootstrap 95% interval within [-10%, +10%]; residual <1%.
- Changes below are `100 * (phases / whole - 1)`. Bootstrap: 5,000 seeded
  resamples of six pairs, not pooled operation samples.

| Backend | Median paired change | Bootstrap 95% interval | Result |
| --- | ---: | ---: | --- |
| BFS | -9.53% | [-22.94%, -2.04%] | **Fail** |
| ETT | +0.53% | [-0.99%, +6.54%] | Pass |
| HDT | +2.73% | [-2.31%, +34.96%] | **Fail** |

BFS's six phase runs were all faster than their whole controls:
-1.22%, -5.70%, -24.58%, -2.86%, -21.30%, -13.36%.
This is **not an optimization result**: no graph optimization was present.
It is evidence that these controls cannot certify stable attribution at the
chosen thresholds.

HDT's adverse pair is retained:
[phase](calibration/000-hdt-1-adapter-phases.json) **17.147500 ms** versus
[whole](calibration/001-hdt-1-adapter-whole.json) **10.738250 ms**, **+59.69%**.
Its six changes were -4.25%, +59.69%, +5.42%, +10.23%, -0.36%, +0.03%.

The failure cannot be assigned solely to clock cost, host noise or compiler
layout from these data. Load averages were approximately 3.08 before and 3.15
after, lower than the first attempt, yet the gate still failed. The shared host
was not exclusive, and lower load does not establish controlled frequency,
scheduling or allocator state. Do not assume that merely retrying will fix it.

The collector returned failure only after preserving all raw observations.
The planned **72 topology-baseline processes and 36 facade-limit processes
were not run**. No gate was relaxed, pair replaced, or follow-up recording made.

## Descriptive dense observations, not an accepted baseline

Six phase-instrumented runs per backend. Setup medians and quartiles are in ms;
peak RSS is the fresh build-only **whole child process**, including input/JSON,
runtime, allocator and reporting, not engine heap or phase-specific memory.

| Backend | Setup median [Q1, Q3] | Setup min-max | Total initialization median | Peak RSS median, MiB |
| --- | ---: | ---: | ---: | ---: |
| BFS | 1.232 [1.227, 1.239] | 1.211-1.350 | 2.413 | 5.22 |
| ETT | 5.164 [5.118, 5.212] | 5.103-5.238 | 6.378 | 16.42 |
| HDT | 7.845 [7.282, 8.160] | 7.111-17.148 | 9.071 | 32.52 |

Median phase times in microseconds; separate medians do not necessarily sum:

| Phase | BFS | ETT | HDT |
| --- | ---: | ---: | ---: |
| Input generation | 136.521 | 135.438 | 152.083 |
| Trace encoding/fingerprint/disposal | 1,037.479 | 1,026.479 | 1,113.208 |
| Node vector | 0.229 | 0.291 | 0.167 |
| Adapter map/validation | 4.042 | 5.500 | 5.458 |
| Backend creation + registration | 12.104 | 19.605 | 25.583 |
| Constructor return/map cleanup | 1.333 | 1.333 | 1.396 |
| Initial edge insertion | 1,213.854 | 5,135.479 | 7,812.333 |
| Residual bookkeeping | 1.417 | 1.458 | 1.500 |

Edge insertion remains the clearly largest **observed dense setup interval**:
median shares **98.46% BFS, 99.47% ETT, 99.55% HDT**. Even the minimum observed
shares exceed 98%. This supports a coarse descriptive finding, not reproducible
optimization deltas or a ranking of inner functions. Sub-microsecond node-vector
differences are not useful backend comparisons.

Sparse, cyclic and disconnected fixtures are implemented and correctness-tested,
but their phase dominance and memory costs remain **unmeasured**. No claim is
made that dense dominance generalizes to them.

## Engineering recommendation and acceptance

**No Phase-1 optimization yet.** The next work should establish why whole and
phased controls disagree, using a separately approved diagnostic protocol:
measure an identical-path A/A noise floor and inspect possible compiler/code-path
perturbation, preferably on an exclusive host. Do not silently remove outliers,
change thresholds retrospectively, or continue retrying this campaign.

For the dense case alone, the evidence argues against prioritizing adapter-map
removal or vertex registration in isolation: their combined observed share is
too small to reach the design's 5% setup target. Edge-loading changes have the
strongest directional support. Shared indexed-edge insertion to reduce repeated
endpoint work remains the smallest candidate, but its benefit is unmeasured.
There is no basis here to prefer a DSU, direct Euler-tour construction, or a
library replacement; allocation and forest-maintenance costs were not isolated.

Acceptance before an optimization:

1. Validate measurement stability under a prospectively declared protocol and
   retain both failed attempts. Exact accounting, graph identity, and passing
   correctness checks are necessary but not sufficient.
2. Complete the bounded four-topology, three-backend baseline and separate
   default/configured-limit comparison. Report every phase's variability and
   build-only process RSS without claiming engine-only heap.
3. Subsequently apply the design's candidate gate: >=5% median total-core-setup
   reduction with paired 95% CI below zero on a preselected target; no confirmed
   >5% dynamic slowdown or >10% fresh build-only RSS increase in controls.
   Preserve all incremental semantics and differential/invariant tests.

No implementation or API changes were added in this replication. Both attempts'
raw evidence is retained; no commit or push was made.
