# Compact BFS workspace: before / after — 2026-10-04

The original connectivity campaign is retained unchanged as the reference.
This experiment adds optional `BfsWorkspace` and `Graph::connected_with_workspace`.
The existing `Graph::connected`, default engine and HTTP server remain unchanged.
The benchmark selector `compact-workspace` measures the optional API.

## Decision and measured outcome

Keep generation-mark workspace **opt-in**, not a replacement default. It improves
all 36 sparse scenario/regime cells in this run (4.3%–46.2% less replay runtime),
both Cogentco cells (33.8%–39.9% less), and all four immediate-repeat cells
(16.6%–24.9% less). These are median process runtimes with limited trials, not
confidence intervals or universal speedups.

Dense results are mixed. The initial two-trial pass had extreme fluctuations
(-77.6% to +390.2%). It is preserved in comparison.json. A separately recorded
four-trial confirmation improves 12/24 dense cells and regresses 12/24, spanning
-14.5% to +9.4%. It does not overwrite or pool the original pass. The confirmation
was selected after observing variance and is an adaptive follow-up, not an
independent prespecified replication. Range overlap is exposed in the table.

The first strategy (v1) reset touched marks after each traversal. It improved
31/36 sparse cells but regressed on the 100k cyclic-block trace by 11%–14%.
Its [full comparison](../2026-10-04-workspace-comparison/comparison.json) and four
raw collections remain available. v2 replaces that reset with u32 generation
marks. No successful or unsuccessful result was discarded.

## Fair comparison and preserved reference

`before` = unchanged compact BFS in the same binary as `after`; `after` = workspace
v2. The original campaign's compact results are also stored as `historical` in
both comparison JSON files, with a separate baseline-drift percentage. We never
attribute historical machine drift to the new API. Every matching cell retains
the original trace fingerprint, operations, seed, node count and warmup/repeat
regime. There were 272 v1 processes, 272 initial v2 processes and 192 dense
confirmation processes: **736 measured processes, all successful**.

Percentages are `100*(after/before-1)`: negative is less runtime/latency/RSS,
positive is more. Runtime is replay wall time including dispatch, assertions,
timers and sampling, excluding graph setup and input validation. Query repeats
are included in replay runtime only for the separate repeat supplement.

The synthetic initial passes use two trials per engine/regime; Cogentco and dense
confirmation use four. Each replay creates a new workspace, so even warmed runs
include initial workspace growth in the first measured non-reflexive query.
Warmup can affect process/allocator/CPU caches, but does not prefill the measured
workspace. The workload sizes and limited seeds remain exploratory.

## Implementation and memory tradeoff

The caller supplies exclusive mutable workspace, allowing other callers to query
the shared immutable graph with separate workspaces. It retains no answers.
Queue allocation is reused; generation marks avoid per-query clearing. Marks
use four bytes per registered vertex versus one byte per `bool` in v1. Counter
rollover clears the entire retained mark array. Tests cover early success,
unknown nodes, reflexive queries, mutations, growth, different graph index maps,
concurrent shared queries and rollover that requires visiting a marked intermediate
vertex. Workspaces retain capacity until dropped.

RSS is peak whole-process memory, not workspace bytes. Export/setup buffers can
dominate this peak; small negative RSS deltas do not mean that four-byte marks
consume less memory than the original boolean vector. Setup and all operation
counts, totals, p50/p95/p99, RSS and observed ranges are retained in the JSON.
No allocation-count profiler was used; allocation reuse is an implementation
property, not a claimed measured allocations-per-second result.

## Every compared cell

Dense rows below use the labelled four-trial confirmation. Other rows use the
initial v2 pass. `separated` means observed runtime ranges do not overlap;
this is descriptive, not statistical significance. `n/a` means no samples or a
zero baseline denominator, never zero cost.

| Scenario / regime | Runtime before→after ms | Runtime Δ | Query p99 Δ | Cut p99 Δ | Link p99 Δ | RSS Δ | Runtime ranges |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| sustained-churn-blocks-v1 / 1024 / q10 / fresh | 0.199→0.149 | -25.4% | -72.5% | -14.4% | -9.4% | +0.2% | separated |
| sustained-churn-blocks-v1 / 1024 / q10 / warmed | 0.144→0.111 | -23.0% | -38.8% | -16.4% | -0.3% | +0.5% | separated |
| sustained-churn-blocks-v1 / 1024 / q50 / fresh | 0.423→0.306 | -27.7% | -54.7% | +14.4% | +11.2% | -0.1% | separated |
| sustained-churn-blocks-v1 / 1024 / q50 / warmed | 0.351→0.227 | -35.4% | -23.4% | +48.8% | -12.6% | -0.1% | separated |
| sustained-churn-blocks-v1 / 1024 / q90 / fresh | 0.699→0.474 | -32.2% | -30.1% | -24.9% | +22.1% | -0.5% | separated |
| sustained-churn-blocks-v1 / 1024 / q90 / warmed | 0.698→0.483 | -30.8% | -29.0% | +29.7% | +41.8% | +0.0% | separated |
| sustained-churn-blocks-v1 / 10000 / q10 / fresh | 0.307→0.247 | -19.5% | -46.6% | -10.1% | +0.0% | -1.0% | separated |
| sustained-churn-blocks-v1 / 10000 / q10 / warmed | 0.260→0.223 | -14.3% | -22.4% | -12.3% | +0.0% | -0.7% | separated |
| sustained-churn-blocks-v1 / 10000 / q50 / fresh | 0.973→0.709 | -27.1% | -11.8% | +0.0% | -37.5% | +0.9% | separated |
| sustained-churn-blocks-v1 / 10000 / q50 / warmed | 0.865→0.784 | -9.4% | +72.2% | +50.6% | +1366.6% | -0.2% | overlap |
| sustained-churn-blocks-v1 / 10000 / q90 / fresh | 2.977→2.325 | -21.9% | -21.7% | +6.4% | +0.0% | +0.2% | separated |
| sustained-churn-blocks-v1 / 10000 / q90 / warmed | 2.951→2.272 | -23.0% | -9.3% | -10.9% | -28.6% | -0.6% | separated |
| sustained-churn-blocks-v1 / 100000 / q10 / fresh | 0.920→0.735 | -20.1% | -5.6% | -9.6% | -0.2% | -0.6% | separated |
| sustained-churn-blocks-v1 / 100000 / q10 / warmed | 0.849→0.671 | -21.0% | -9.3% | -23.4% | -7.2% | -0.7% | separated |
| sustained-churn-blocks-v1 / 100000 / q50 / fresh | 8.187→4.405 | -46.2% | -21.1% | -66.7% | -66.0% | -1.3% | separated |
| sustained-churn-blocks-v1 / 100000 / q50 / warmed | 5.153→4.335 | -15.9% | -3.3% | -12.4% | -22.1% | -0.6% | separated |
| sustained-churn-blocks-v1 / 100000 / q90 / fresh | 24.568→23.071 | -6.1% | -0.0% | +16.1% | n/a | -0.4% | separated |
| sustained-churn-blocks-v1 / 100000 / q90 / warmed | 24.524→22.776 | -7.1% | -1.4% | +256.7% | n/a | -0.3% | separated |
| sustained-churn-path-v1 / 1024 / q10 / fresh | 0.135→0.115 | -14.6% | -63.4% | -14.4% | +0.0% | +0.5% | separated |
| sustained-churn-path-v1 / 1024 / q10 / warmed | 0.106→0.096 | -9.8% | -18.4% | -19.6% | -12.6% | +1.2% | separated |
| sustained-churn-path-v1 / 1024 / q50 / fresh | 0.208→0.150 | -28.0% | -68.9% | +0.0% | +39.5% | -0.3% | separated |
| sustained-churn-path-v1 / 1024 / q50 / warmed | 0.183→0.142 | -22.4% | -56.0% | +0.0% | +28.9% | -0.3% | separated |
| sustained-churn-path-v1 / 1024 / q90 / fresh | 0.504→0.329 | -34.6% | -37.4% | +8.9% | -26.6% | +0.0% | separated |
| sustained-churn-path-v1 / 1024 / q90 / warmed | 0.475→0.292 | -38.5% | -20.8% | +0.4% | +0.3% | +0.7% | separated |
| sustained-churn-path-v1 / 10000 / q10 / fresh | 0.212→0.192 | -9.3% | -42.0% | +85.3% | +0.0% | +0.6% | overlap |
| sustained-churn-path-v1 / 10000 / q10 / warmed | 0.197→0.175 | -11.1% | -17.1% | +33.2% | -80.3% | -0.1% | separated |
| sustained-churn-path-v1 / 10000 / q50 / fresh | 0.708→0.502 | -29.0% | -8.9% | -20.1% | +8.4% | -0.1% | separated |
| sustained-churn-path-v1 / 10000 / q50 / warmed | 0.663→0.478 | -27.9% | -11.5% | -14.1% | +0.0% | -0.2% | separated |
| sustained-churn-path-v1 / 10000 / q90 / fresh | 2.753→2.172 | -21.1% | -10.9% | +21.4% | n/a | -0.1% | separated |
| sustained-churn-path-v1 / 10000 / q90 / warmed | 2.558→2.301 | -10.1% | +4.0% | +63.3% | n/a | +0.6% | separated |
| sustained-churn-path-v1 / 100000 / q10 / fresh | 0.819→0.766 | -6.5% | +14.8% | +177.6% | -4.8% | -0.4% | overlap |
| sustained-churn-path-v1 / 100000 / q10 / warmed | 0.764→0.672 | -12.0% | +15.2% | +52.3% | -4.9% | -0.4% | overlap |
| sustained-churn-path-v1 / 100000 / q50 / fresh | 4.514→3.929 | -13.0% | -3.6% | -27.9% | +5.6% | -0.3% | separated |
| sustained-churn-path-v1 / 100000 / q50 / warmed | 4.836→3.917 | -19.0% | -2.9% | -77.7% | -5.3% | -0.1% | separated |
| sustained-churn-path-v1 / 100000 / q90 / fresh | 23.532→22.523 | -4.3% | +3.2% | -9.5% | n/a | -0.5% | separated |
| sustained-churn-path-v1 / 100000 / q90 / warmed | 23.208→21.993 | -5.2% | -3.6% | +3.7% | n/a | -0.2% | separated |
| sustained-churn-blocks-v1 / 10000 / q90 / fresh / repeats=2 | 8.519→6.410 | -24.7% | -22.3% | -48.0% | -26.3% | +0.3% | separated |
| sustained-churn-blocks-v1 / 10000 / q90 / warmed / repeats=2 | 8.692→6.526 | -24.9% | -21.9% | -20.9% | +12.4% | +0.8% | separated |
| sustained-churn-path-v1 / 10000 / q90 / fresh / repeats=2 | 7.777→6.325 | -18.7% | -6.1% | +72.7% | n/a | -0.7% | separated |
| sustained-churn-path-v1 / 10000 / q90 / warmed / repeats=2 | 7.629→6.363 | -16.6% | -2.0% | -43.6% | n/a | -0.2% | separated |
| topology-zoo-outages-v1 / 197 / qNone / fresh | 1.065→0.705 | -33.8% | -22.1% | +0.0% | +0.0% | +0.7% | separated |
| topology-zoo-outages-v1 / 197 / qNone / warmed | 0.959→0.576 | -39.9% | -31.8% | +19.6% | +14.0% | +0.6% | separated |
| dense-bridge-churn-v1 / 128 / q10 / fresh | 0.180→0.165 | -8.4% | -12.1% | +0.0% | +0.0% | +0.2% | separated |
| dense-bridge-churn-v1 / 128 / q10 / warmed | 0.171→0.158 | -7.5% | -6.3% | +0.0% | +0.0% | -0.5% | separated |
| dense-bridge-churn-v1 / 128 / q50 / fresh | 0.721→0.672 | -6.7% | +1.6% | +0.8% | +48.8% | +0.3% | overlap |
| dense-bridge-churn-v1 / 128 / q50 / warmed | 0.720→0.652 | -9.5% | -2.4% | +0.0% | +98.8% | -0.1% | separated |
| dense-bridge-churn-v1 / 128 / q90 / fresh | 1.187→1.107 | -6.8% | -5.4% | -15.5% | +19.6% | -0.6% | separated |
| dense-bridge-churn-v1 / 128 / q90 / warmed | 1.199→1.094 | -8.7% | +2.3% | -24.6% | -19.6% | -0.7% | separated |
| dense-bridge-churn-v1 / 512 / q10 / fresh | 1.937→2.119 | +9.4% | +10.7% | -19.6% | +48.8% | -0.6% | overlap |
| dense-bridge-churn-v1 / 512 / q10 / warmed | 1.951→1.981 | +1.5% | +5.6% | +0.0% | -32.8% | -0.7% | overlap |
| dense-bridge-churn-v1 / 512 / q50 / fresh | 9.435→10.255 | +8.7% | +11.2% | +33.6% | +16.8% | -0.1% | separated |
| dense-bridge-churn-v1 / 512 / q50 / warmed | 9.515→9.584 | +0.7% | -1.4% | +0.0% | +0.0% | +0.0% | overlap |
| dense-bridge-churn-v1 / 512 / q90 / fresh | 17.300→18.450 | +6.6% | +8.5% | +0.0% | +100.0% | -0.1% | separated |
| dense-bridge-churn-v1 / 512 / q90 / warmed | 17.139→18.273 | +6.6% | +3.8% | -15.3% | -0.2% | +0.8% | overlap |
| redundant-bridge-churn-v1 / 128 / q10 / fresh | 0.182→0.167 | -8.4% | -16.8% | -32.8% | +0.0% | -0.3% | overlap |
| redundant-bridge-churn-v1 / 128 / q10 / warmed | 0.180→0.161 | -10.5% | -7.0% | +0.0% | +0.0% | +0.3% | separated |
| redundant-bridge-churn-v1 / 128 / q50 / fresh | 0.721→0.665 | -7.7% | -5.4% | +0.6% | +0.0% | -0.2% | overlap |
| redundant-bridge-churn-v1 / 128 / q50 / warmed | 0.719→0.659 | -8.3% | -5.5% | +0.0% | +0.0% | +0.1% | separated |
| redundant-bridge-churn-v1 / 128 / q90 / fresh | 1.219→1.112 | -8.8% | -13.4% | -41.0% | +0.0% | -0.1% | separated |
| redundant-bridge-churn-v1 / 128 / q90 / warmed | 1.207→1.031 | -14.5% | -14.9% | -25.1% | -19.6% | +0.8% | separated |
| redundant-bridge-churn-v1 / 512 / q10 / fresh | 1.957→2.087 | +6.7% | +5.2% | +0.0% | +0.0% | -0.9% | separated |
| redundant-bridge-churn-v1 / 512 / q10 / warmed | 1.955→2.011 | +2.9% | +12.8% | +0.0% | +0.0% | -0.5% | overlap |
| redundant-bridge-churn-v1 / 512 / q50 / fresh | 9.614→10.230 | +6.4% | +12.7% | +14.4% | +50.0% | +0.2% | overlap |
| redundant-bridge-churn-v1 / 512 / q50 / warmed | 9.408→10.021 | +6.5% | +1.5% | +0.0% | -33.3% | +0.9% | overlap |
| redundant-bridge-churn-v1 / 512 / q90 / fresh | 17.449→18.128 | +3.9% | -5.8% | -22.3% | -78.9% | +0.6% | overlap |
| redundant-bridge-churn-v1 / 512 / q90 / warmed | 17.112→17.241 | +0.8% | -0.2% | -28.6% | +54.5% | +0.2% | overlap |

## Reproduction and verification

- [Initial v2 comparison](comparison.json), rebuilt by `python3 compare.py`.
- [Dense confirmation](dense-confirmation.json), rebuilt by `python3 compare_dense_confirmation.py`.
- Sibling `2026-10-04-workspace[-v2]-{sparse,dense,repeats,cogentco}` manifests
  preserve exact commands, sources/patches, binaries, measurements and trace hashes.
- `2026-10-04-workspace-v2-dense-confirmation` records the adaptive repeat.
- [Audit](audit.json) checks original and new artifacts, matching traces, and the
  unchanged default BFS function. Local ignored traces are needed for full audit.
- [Persistent before/after policy](../../docs/experiments/2026-10-04-before-after-policy.md)
  applies to subsequent HDT and ETT work: new directories, unchanged reference,
  same traces, gains and regressions, latency tails, startup and memory.

A review caught an ineffective rollover test; it was strengthened after the initial
v2 measurements and before the dense confirmation. The production algorithm did
not change between those runs; source snapshots retain each exact test revision.

HDT follow-up: [diagnostic profiling is now recorded](../2026-10-04-hdt-followup-profile/README.md), using the same
cyclic-block/path reference traces plus a separate longer CPU sample. Dense controls
remain mandatory for the next HDT change. Then ETT candidate-search/storage profiling.
Neither algorithm has been modified by this workspace experiment. Do not infer
service-level improvements until callers explicitly adopt and measure the API.
