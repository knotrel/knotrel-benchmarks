# Knotrel v0.5.0 performance qualification protocol (M10)

**Status: FROZEN before the final collection** (freeze record at the end).
Written after two bounded pilots used only to size windows and estimate
runtime. No threshold, exclusion, seed or rule below was chosen after seeing
a final result. The v0.4.0 maintainer waivers do not carry forward.

## 1. Identities

| Item | Identity |
|---|---|
| Candidate (C) | knotrel `ea127069b202c6c69a3a2dd71fefafcd18cfeda4`, branch `feature/v0.5.0-node-edge-lifecycle`, workspace 0.5.0 |
| Baseline for A (B) | tag `v0.4.0`, commit `556683c8beb1ffe90fbf645bcf7955880690df2c` (released 2026-11-15) |
| A harness | knotrel-benchmarks `df635a1e` (core harness, as in v0.4.0) with derived lockfiles that change only the `knotrel-core` version |
| A collector and analysis | `run_p0_aa.py` and `prepare_bc_qualification.py` byte-identical to the v0.4.0 collector; `analyze_bc_qualification.py` with only the later path-containment fix (outputs unchanged) |
| B/C tooling | knotrel-benchmarks `5c35360f38fba10ed783ec641c78d4b44bf460bf` (branch `feature/v0.5.0-lifecycle-qualification`): `tools/lifecycle-probes`, `scripts/{run,analyze}_lifecycle_qualification.py`, `scripts/derive_lifecycle_window_multipliers.py` |
| Window multipliers | `window-multipliers.json`, sha256 `9a597ab60002bd9eb94ecd4d2deffa6e9291d009222bb67c7bbbea92eb214486` (from pilot 3) |
| Toolchain | rustc 1.100.0 (`+1.100.0`), release profile, `--locked` |
| Host | Apple M3, macOS 26.5.2, AC power, no concurrent builds or campaigns |

Every probe prints the linked knotrel revision and the probe source
(knotrel-benchmarks) revision, each with its dirty state, first; the analysis
rejects a run whose builds do not name the candidate and the frozen tooling
commit, both clean.

## 2. Experiment A: existing behavior against v0.4.0

**Question:** with lifecycle support disabled (the default), did existing
operations regress against v0.4.0?

**Design:** the v0.4.0 qualification design, unchanged: nine cells (core
sparse traversal and sustained churn on `compact-bfs` and
`compact-workspace`; HTTP standalone batches 1, 8, 64, 256; HTTP lifecycle
startup), 12 pairs per cell in three seeded sessions, balanced order, fresh
processes. Session seeds 130500-130502; extension seeds 130510-130512.

**Thresholds and their applicability (recorded before execution):** these
cells measure exactly the existing operations in the default configuration,
so the existing tolerances apply: primary 10%, p99 25%, RSS 20%. Rules:
v0.4.0 G3/G3a-1 (`--rules v0.4.0`): REPORT_ONLY for the timer-limited core
`link_p99_ns` and `cut_p99_ns`; one extension of 12 pairs per cell with any
INCONCLUSIVE gated metric; INCONCLUSIVE_DISCLOSED only for an INCONCLUSIVE
primary with median ≤ t and every supporting metric PASS; otherwise
UNRESOLVED; any REGRESSION wins. REGRESSION and UNRESOLVED need an owner
decision.

**Not covered by A:** the experimental `ett` and `hdt` engines, feeder and
import paths, and metrics-enabled operation have no release-to-release cell.
Their lifecycle-mode costs are covered by B2 and B4; a comparison with v0.4.0
is disclosed as not measured.

## 3. Experiment B: lifecycle cost

**Question:** what do lifecycle operations and lifecycle mode cost against a
semantically equivalent reference?

**Pairing.** Every B1-B4 cell is paired in-process. For each pair both arms
are built fresh from the same topology (untimed); each then replays the same
pre-generated trace once (timed), alternating which arm runs first (6 and 6).
2 warmup pairs are discarded; 12 are analyzed. Core cells verify before any
timing that both arms give identical per-operation result digests and
identical end states (counts plus `connected` on 200 sampled pairs), and
re-check the digest on every replay. HTTP cells compare `connected` answers
on 200 random pairs after both windows of every pair.

| Group | Candidate | Reference | Matrix | t |
|---|---|---|---|---|
| B1 lifecycle operations (core) | `LifecycleGraph` | application-side lifecycle over a plain `ConnectivityGraph`: the same registered topology and flags in hash maps, effective edges in the engine, same results and error precedence, never compacts | 3 engines × {sparse, ring, hub} × {1k, 10k, 100k} × {query-heavy 90/10, mutation-heavy 10/90}, base window 4,000 operations; plus fresh-ID churn on sparse 1k (8,000) and 10k (48,000), sized for at least one compaction per window | 25% |
| B2 opt-in cost on legacy operations (core) | `LifecycleGraph` | plain `ConnectivityGraph` | 3 engines × {sparse, ring, hub} × {1k, 10k, 100k}; legacy trace 50% `connected`, 50% `link`/`cut`; base window 4,000 | 50% |
| B3 degree effects | `LifecycleGraph` | application-side reference | 3 engines × star of degree {16, 256, 4,096, 16,384} with a path among the leaves: `degree` repeats deactivate / query / reactivate of the center (about 3,000 / 600 / 300 / 60 operations); `degree-remove` repeats remove, re-register and re-link the center to every leaf (200 / 20 / 2 / 1 cycles) | 25% |
| B4 HTTP and feeder (in-process router) | see below | see below | 3 engines × {sparse, hub} × 10k per scenario; `compact-bfs` sparse 100k for the lifecycle scenarios and imports; high-inactive import (60% inactive, 30% disabled) × 3 engines; metrics scenarios × 3 engines | see below |

B4 scenarios (base request counts before scaling):

| Scenario | Candidate | Reference | t |
|---|---|---|---|
| `optin-mutation` | lifecycle server, 40 batches of 1,024 alternating `cut`/`link` | plain server, same requests | 50% |
| `optin-query` | lifecycle server, 4 batches of 1,024 `connected` | plain server, same requests | 25% |
| `ops` | lifecycle server, mutation-heavy lifecycle trace without queries in batches of 256 (`40 × 256` trace operations before removing queries, so about 36 batches) | plain server plus an application-side planner with the same registered topology and flags sending the equivalent `link`/`cut` | 25% |
| `ops-query` | lifecycle server, query-heavy lifecycle trace (90% `connected`), batches of 256 | the planner answers `connected` locally when an endpoint is inactive or absent and forwards the rest | 25% |
| `events` | lifecycle feeder events, 128 per request | plain source-managed server with the planner's equivalent legacy events, up to 1,024 per request | 25% |
| `import` | imports with 20% inactive nodes and 10% disabled edges, one fresh server per import | plain imports of the effective graph; the application's lean flag store (registered edge list, a node flag vector, an edge flag vector) is copied once per import inside the reference window | 100% |
| `import-optin` | all-active legacy imports on a lifecycle server | same payload on a plain server | 100% |
| `metrics-ops` | `ops` requests on a lifecycle server with metrics enabled | same, metrics disabled | 6% |
| `metrics-legacy` | `optin-mutation` requests, lifecycle disabled, metrics enabled | same, metrics disabled | 6% |

**Window sizing (from pilot 3, before freezing).** For every B1-B4 cell
whose faster arm's pilot median window was below 2 ms, the window (B1-B3) or
request or import count (B4) is multiplied by the smallest power of two that
reaches 2 ms, at most 64 (`window-multipliers.json`: 44 of 167 cells scaled,
none at the cap). Only window durations were used; no ratio was inspected.
Scaling a core window lengthens the trace, so a scaled cell's trace reaches
states the base trace does not; the scale is reported with each cell.

**Classification.** Paired log ratios `ln(candidate / reference)`, the
v0.4.0 interval `[r(3), r(10)]` at n = 12 (`summarize_metric` reused
unchanged): PASS if the upper bound ≤ ln(1 + t), REGRESSION if the lower
bound > ln(1 + t), otherwise INCONCLUSIVE. A cell whose median window in
either arm is below 1 ms is TIMER_LIMITED: numbers reported, no verdict. **No
extension and no rerun** for B.

**Why these tolerances.** No numerical guarantee exists for new operations.
25% (the existing p99 tolerance) screens whether the facade costs more than
the equivalent application-side code. The opt-in bounds budget lifecycle mode
on legacy operations: the catalog adds bookkeeping to every mutation (50%)
and only flag checks to queries (25%); imports build the catalog besides the
engine (100%). 6% is the upper-bound budget pre-approved for the v0.4.0
metrics overhead (median ≤ 3% is reported too).

**Known asymmetries, disclosed with the results:**
- `ops`, `ops-query` and `events`: the reference's planning is untimed, which
  favors the reference; a REGRESSION there is an upper bound on the
  candidate's extra cost, not attributable to server work alone.
- `events`: request counts differ (128 lifecycle events per request against
  up to 1,024 legacy events), so per-request overhead differs.
- `import`: the reference imports fewer edges (the effective graph) and keeps
  the flags in the application in a lean store copied once per import; a
  heavier application store would favor the candidate.
- B1 reference never compacts; fresh-churn cells include the candidate's
  compaction rebuilds, which the reference does not perform.
- HTTP arms stay alive during both windows; every request crosses the
  server's blocking-pool hop.

**B5 memory.** Net live heap after building the all-active 100k-node graph
(`count-alloc` build; baseline after generating the topology subtracted;
deterministic, one run) for plain, lifecycle and reference, 3 engines ×
{sparse, hub}. **Budget:** lifecycle ≤ 3.0 × plain, else FAIL.

## 4. Experiment C: sustained resources

**Question:** do repeated deactivation, removal and ID reuse grow storage
without bound?

3 engines × ({sparse} × {1k, 10k, 100k} ∪ {ring, hub} × {100k}) × churn
mode, 30 cycles of 5% of the live IDs, lifecycle and reference arms:
- `fresh`: remove the node, register a never-used ID with `floor(2E/V)`
  random edges;
- `same`: remove and re-register the same ID the same way;
- `toggle`: restore the previous cycle's picks, then deactivate new picks and
  disable one enabled incident edge of each, so about 5% of the nodes stay
  inactive across checkpoints with as many edges disabled.

The whole schedule and the expected logical counts after every cycle are
computed first by an independent model, which is then dropped; a heap and
RSS baseline is recorded before the arm is built. Checkpoints after
construction and after every cycle report logical counts, expected counts,
storage diagnostics (`LifecycleStorage`: engine vertices, retired slots,
catalog node capacity, incident entries and capacity), net live heap
(`heap` variant, `count-alloc`) and net RSS (`rss` variant, mimalloc).

| Check | Arm | Rule | Outcome |
|---|---|---|---|
| C1 engine slots | lifecycle | `engine_vertices ≤ 2 × nodes + 1024` at every checkpoint | PASS/FAIL |
| C2 logical counts | both | counts equal the expected counts at every checkpoint | PASS/FAIL |
| C3 heap growth | lifecycle | net heap: max over cycles 21-30 ≤ 1.25 × max over cycles 1-10, and least-squares slope over cycles 1-30 × 30 ≤ 10% of the mean over cycles 1-10 | PASS/FAIL |
| C4 RSS growth | lifecycle | same rules on net RSS | PASS / EXCEEDS_BUDGET (disclosure: allocator retention) |

The reference arm's resources are reported without a verdict. Logical
counts, retained capacities, heap and RSS are reported separately and never
substituted for one another.

## 5. Ordering, host state, validation and failure handling

- Experiments run sequentially: A main, A extension if triggered, then all
  B and C cells in one collector run shuffled with order seed 50500. No other
  campaign or build runs meanwhile; the host is kept awake with
  `caffeinate`.
- The collector records power, thermal state and load before every cell and
  every child's argv, exit status, stdout and stderr.
- The analysis rejects a run that is not the complete `final` profile, lacks
  any cell, has a nonzero exit, was not on AC power, used other window
  multipliers, or contains a build record that does not name the clean
  candidate.
- A failing child stops the collection. One rerun per experiment is allowed
  only for an infrastructure failure unrelated to the measured code, and is
  recorded with its cause. A failure that reproduces is a result.

## 6. Budget

Aggregate measured runtime is capped at six hours (builds excluded). Pilot 1
took 116 s (188 cells), pilot 2 159 s and pilot 3 165 s (365 cells), all at
two pairs and three cycles; pilot 3 used the final tooling. The projected final B/C runtime is about 30 minutes; A's main
phase and extension took about 13 minutes each for v0.4.0.

## 7. Claims

Results apply only to the measured host, toolchain, configurations and
workloads. No general speedup or slowdown claim is made. Absolute values are
reported beside every percentage.

## 8. Re-assessment after later changes

Documentation-only commits after the final collection do not change binaries;
before declaring the evidence applicable to the release commit, its executed
code is compared with the measured candidate (as for v0.4.0). A code change
invalidates the affected evidence.

## Freeze record

Frozen 2026-11-16T00:24:59Z before any final measurement of A, B or C.

- Candidate: knotrel `ea127069b202c6c69a3a2dd71fefafcd18cfeda4`, clean.
  Local validation of this commit passed all 14 steps
  (`evidence/v0.5.0-dev/validation/summary.txt`).
- B/C probe binaries (built from tooling `5c35360f`, embedding both
  revisions, clean):

| Binary | sha256 |
|---|---|
| `tools/lifecycle-probes/target/release/core-lifecycle` | `46451a81a5d84ed021bc633687ff04dbf93d74ffba957197d75e485a629a4b2a` |
| `tools/lifecycle-probes/target-count/release/core-lifecycle` | `5179f1f09f3f4e8404f4a516835885f09970b0401475288d2a480f3e8659a280` |
| `tools/lifecycle-probes/target/release/http-lifecycle` | `8637730c9dd6b5d6848992350fbf44742d451f30c578ddc3dba43b3420bd44d9` |

- A campaign directory: `/Users/rt/workspace/knotrel/evidence/v0.5.0-qualification/A-20261116T001606Z-ea12706` (plan and dry-run preflight passed;
  `identities.json` records every binary and lockfile).
- Order seed for B/C: 50500. A session seeds: 130500-130502 (extension
  130510-130512).
- Analysis command for B/C:
  `analyze_lifecycle_qualification.py RUN --expect-knotrel-rev ea127069b202c6c69a3a2dd71fefafcd18cfeda4 --expect-multipliers-sha256 9a597ab60002bd9eb94ecd4d2deffa6e9291d009222bb67c7bbbea92eb214486 --expect-probes-rev 5c35360f38fba10ed783ec641c78d4b44bf460bf`.
- Pre-collection reviews: independent tooling review (4 blockers, all
  resolved) and re-review (2 new majors, resolved in `5c35360f`).

## Amendment 1: re-qualification of candidate 6494253

Recorded 2026-11-16T01:20:05Z, before any measurement of candidate
`649425373a510a3a18c25519d21c5cf8b43e13fe`.

**Why.** Run 1 (candidate `ea12706`) completed under this protocol and is
preserved unchanged in `evidence/v0.5.0-qualification/RUN-1-ea12706.md`,
`BC-final-ea12706/` and `A-20261116T001606Z-ea12706/`. It found 31 B
REGRESSIONs. Diagnostic comparisons, not used for any verdict, traced most of
them to two facade defects (identity-hashed catalog; ascending cut order),
fixed in knotrel `6494253` (`perf(core)` commit). Run 1's results remain the
record for `ea12706` and are reported.

**What is unchanged:** the matrix, every rule, tolerance and budget, the
analysis code, A's seeds (130500-130502, extension 130510-130512) and the B/C
order seed (50500).

**What changes:** the candidate; the window multipliers, re-derived by the
same mechanical rule from pilot 4 on the new candidate
(`evidence/v0.5.0-qualification/pilot4-6494253`, 149.6 s; 46 of 167 cells
scaled, none at the cap): `window-multipliers-6494253.json`, sha256
`4509c4a06573eba776e382568026c57078ca1a7205670fb8fcd4b4bf473ad410`; and the
probe binaries, rebuilt from unchanged probe sources at benchmarks
`450ba04a` (their build records name that revision):

| Binary | sha256 |
|---|---|
| `tools/lifecycle-probes/target/release/core-lifecycle` | `86ef64dd2789497fd2d82bd6412ca70c3dfcfdb8692205a0a7ae58f9c85a8c32` |
| `tools/lifecycle-probes/target-count/release/core-lifecycle` | `0654d03a6ee6a7d5aca4ba2b1099659f502806c1e44a877ab502c748e21f9a8e` |
| `tools/lifecycle-probes/target/release/http-lifecycle` | `43ca88b5cbbfdb207cd945d7551632750c52c859308166ee298d5942ea7ac557` |

- A campaign directory: `/Users/rt/workspace/knotrel/evidence/v0.5.0-qualification/A-20261116T011844Z-6494253` (plan and dry-run preflight passed).
- Local validation of `6494253`: 14/14 steps
  (`evidence/v0.5.0-dev/validation/summary.txt`).
- Analysis command for run 2:
  `analyze_lifecycle_qualification.py RUN --expect-knotrel-rev 649425373a510a3a18c25519d21c5cf8b43e13fe --expect-multipliers-sha256 4509c4a06573eba776e382568026c57078ca1a7205670fb8fcd4b4bf473ad410 --expect-probes-rev 450ba04a142c9b4e9c4765c77d1ca41e4ec57ec4`.
- Measured runtime so far: pilots 1-4 about 10 minutes, run 1 about 42
  minutes; run 2 is projected at about 45 minutes, within the six-hour cap.

## Amendment 2: re-qualification of candidate a1d9577 (B and C)

Recorded 2026-11-16T07:52:31Z, before any final measurement of candidate
`a1d95778f8c876c49efd09dcddcdf6fbdd8259fe`. Found and written **after** the
run-2 results; it applies only to this and later candidates.

**Why.** Run 2 (candidate `6494253`) completed under amendment 1 and is
preserved unchanged (`evidence/v0.5.0-qualification/BC-final-6494253/`,
`A-20261116T011844Z-6494253/`, `REPORT.md`); its verdicts remain the record
for `6494253` and are not re-scored. Frozen diagnostics, not used for any
verdict (`evidence/v0.5.0-remediation/`), found two storage-retention defects
in the `ett`/`hdt` engines (emptied incidence sets kept their B-tree leaf;
HDT upper levels kept isolated vertex records), fixed in knotrel `1ec2de3` and
`9467e0a`, and avoidable bulk-import catalog work, removed in `7f19b11`
(test and documentation follow-up `a1d9577`). Each change has regression
tests and an independent review with no blocker or major finding.

**Tooling correction (B4 `import` reference).** The reference derived its
effective edge list outside the timed window although an application holding
the flags must do that work for every plain import. From this amendment on,
`FlagStore::build` derives it inside the window (probes `7ffadc9e`), and a
derived list that differs from the payload actually sent aborts the probe
(`444806d3`). The derivation costs about 0.03 ms per import (10k nodes); an
independent methodology review estimates that applied to run 2 it could have
moved the borderline `compact-bfs` hub cell (+104.6%, lower bound +102.9%)
to about the budget. This is why it is prospective only.

**Disclosed asymmetries added (not corrected):** the import reference's lean
store has no per-node incidence index (later reactivation/removal scans O(E)),
validates no entries, uses dense IDs and has no atomic publication, while the
`ops`/`events` reference uses an indexed planner; request-body serialization
is untimed in both arms, which favors the candidate end to end. With 60%
inactive and 30% disabled, parsing the non-effective entries the full-topology
contract requires is by itself about three times the reference import on
`compact-bfs` (D3a), so the 100% budget cannot be met there by any
implementation of the contract; these cells are reported as measured and this
mis-specification is reported for an owner decision, without changing the
budget.

**What is unchanged:** the matrix, every rule, tolerance and budget, the
analysis code, the B/C order seed (50500).

**What changes:** the candidate; the probe sources (`444806d3`); the window
multipliers, re-derived by the same mechanical rule from pilot 5 on the new
candidate (`evidence/v0.5.0-qualification/pilot5-a1d9577`, order seed 11,
150.2 s; 47 of 167 cells scaled, none at the cap):
`window-multipliers-a1d9577.json`, sha256
`c134ba472ae4365bdd81bad2b6ed9e2e0ca47177045f053d6141e64b11a8747c`; and the
probe binaries (build records name knotrel `a1d9577` and probes `444806d3`, both clean):

| Binary | sha256 |
|---|---|
| `tools/lifecycle-probes/target/release/core-lifecycle` | `b18b551edf0e3871e3e14e9eca76006925d71e46f22ed58564b493f0ac3535c7` |
| `tools/lifecycle-probes/target-count/release/core-lifecycle` | `53497c21efe4d0ea225e703a78623a2896ea8c7222342619ca3ff1d6410f4565` |
| `tools/lifecycle-probes/target/release/http-lifecycle` | `b0c55f5bbb5fc95e62ad5b530600c5d3a0e7fcf8d5f32b36904cce23ad2505e5` |

**Experiment A is not repeated.** `git diff 6494253 a1d9577 -- crates` touches
only `knotrel-core` `dynamic.rs`, `hdt.rs`, `hdt_profile.rs`, `index.rs`
(used only by `ett`/`hdt`) and `topology.rs` (lifecycle facade). Every A cell
runs `compact-bfs` or `compact-workspace` with lifecycle mode off, whose code
is unchanged; `knotrel-server` is unchanged. Run 2's A results are carried
forward for `a1d9577` as measured, including its 3 UNRESOLVED and 2
INCONCLUSIVE_DISCLOSED cells; repeating A on unchanged code would only re-sample
those cells, which the extension policy does not allow.

- Local validation of `a1d9577`: 14/14 steps
  (`evidence/v0.5.0-dev/validation-a1d9577/summary.txt`).
- Analysis command for run 3:
  `analyze_lifecycle_qualification.py RUN --expect-knotrel-rev a1d95778f8c876c49efd09dcddcdf6fbdd8259fe --expect-multipliers-sha256 c134ba472ae4365bdd81bad2b6ed9e2e0ca47177045f053d6141e64b11a8747c --expect-probes-rev 444806d3071c903b7cec211e094c62952a46eddb`.
- Measured runtime before run 3: about 2 h 20 min of the six-hour cap
  (pilots 1-5, runs 1-2, diagnostics D1-D3).

## Erratum to amendment 2 (recorded 2026-11-16, after run 3)

Amendment 2's paragraph "Experiment A is not repeated" is withdrawn. Unchanged
executed source paths do not establish that A's `6494253` result applies to
`a1d9577`: A's binaries link the changed `knotrel-core`, and binary-layout
sensitivity is documented (v0.4.0 release notes, D1). A campaign for a new
candidate is consistent with amendment 1, and the extension policy limits
extensions for the same candidate, not a first A campaign on a new one. Until a
binary identity check or a new A campaign on `a1d9577` is complete, A has no
result for `a1d9577`. The line "Measured runtime before run 3: about 2 h 20 min"
was an estimate; log-based figures are in `RUN-3-a1d9577.md` (errata E5).
Run 3's concurrent agent activity is recorded in `RUN3-CONCURRENT-ACTIVITY.md`.
