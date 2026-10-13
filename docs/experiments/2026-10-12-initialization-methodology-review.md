# Initialization methodology review and proposed control protocol

**Status:** Review and protocol for approval; not implemented or executed.
**Scope:** Read-only source/binary inspection and reanalysis of the two existing
calibrations. No benchmarks, builds, source changes, or changes to existing
evidence were made for this review.

## 1. Decision

The present whole/phased comparison is **not an isolated measurement of clock
overhead**. It compares two separately compiled construction paths, different
timestamp/bookkeeping work, and different fresh processes under incompletely
observed system conditions. It can estimate their *net setup-time difference*
under a valid randomized experiment, but cannot separate its causes.

The failures should be retained, not interpreted as proof of a particular
instrumentation tax or bypassed by repeated calibration. First measure
identical-path A/A variability. Only then evaluate instrumentation using a
common compiled construction path and an explicit scaffolding control.

Three findings are firm:

1. Timing accounting and graph correctness are necessary but do not establish
   measurement validity.
2. Whole and phased have shared graph semantics and a shared edge-insertion
   loop, **not identical constructor machine code with only clocks added**.
3. Both campaigns put phased HDT in the first process. That process had a
   disproportionate whole-process duration in both campaigns. Position,
   startup/session state and mode are therefore not independently replicated.

## 2. Inspected evidence and implementation

- [First report](../../results/2026-10-12-initialization-phase0/README.md),
  [manifest](../../results/2026-10-12-initialization-phase0/calibration/manifest.json),
  [analysis](../../results/2026-10-12-initialization-phase0/calibration/analysis.json).
- [Replication report](../../results/2026-10-12-initialization-phase0-replication/README.md),
  [manifest](../../results/2026-10-12-initialization-phase0-replication/calibration/manifest.json),
  [analysis](../../results/2026-10-12-initialization-phase0-replication/calibration/analysis.json).
- [Adapter construction](../../crates/knotrel-benchmarks/src/engines.rs#L196),
  [runner](../../crates/knotrel-benchmarks/src/bin/initialization-profile.rs#L118),
  [collector/order/statistics](../../scripts/run_initialization.py#L34),
  [process wrapper](../../scripts/run_scale.py#L32).
- [Release settings](../../Cargo.toml#L31),
  [compiler capture](../../crates/knotrel-benchmarks/build.rs),
  [current methodology](../methodology.md#initialization-phase-diagnostic).

Both datasets have 36 processes: six whole/phased pairs per backend on the same
512-vertex, 65,281-edge dense bridge. The inspected executable matches both
recorded SHA-256 values:
`9992c7104ac1b6875aebe1a18d024b266feae55f48d513dfc893b3e71fe99fc5`.
Both use Rust 1.98.1 on macOS 27.0.1 arm64, thin LTO and one codegen unit;
recorded RUSTFLAGS and release-profile environment overrides are unset.
Source hashes and saved collector copies match the inspected implementation.

### What the compiler actually emitted

Read-only `llvm-nm` and `llvm-objdump` inspection of that executable found:

| Code | Unslid address / observation |
| --- | --- |
| `Engine::new_with_timings` | `0x100019fa8`; 965 static instructions in the function; 896-byte prologue stack reservation |
| `Engine::new` | `0x10001aebc`; 706 static instructions; 432-byte prologue stack reservation |
| Phased constructor call in `measure` | `0x10000dc18` |
| Whole constructor call in `measure` | `0x10000dd00` |
| Shared initial-edge loop | `0x10000e0ac` through `0x10000e0d4`; both modes call the same `Graph::link` at `0x10000e0b8` |
| Shared core BFS registration target | Both constructors call `knotrel_core::Graph::add_node` at `0x10002d7c0` |
| Shared ETT / HDT registration targets | `0x10002bb44` / `0x1000327f4` in both constructors |

These instruction counts cover entire constructor functions, including other
backend/error branches. They are **not executed-instruction counts**, nor an
estimate of the per-run cost difference.

`construct(..., impl FnMut(ConstructionBoundary))` is monomorphized for two
different closures: a no-op and a timestamp recorder. The binary contains
separate constructor layouts and separately named sorting specializations for
their temporary B-tree-map construction. It also has different register/stack
usage and result handling. Mere source reuse does not prevent these differences.
The sorting specializations' existence does not prove their slow paths execute
on the already ordered node list.

Conversely, the edge loop is demonstrably shared, with a conditional timestamp
immediately before it and common core calls. There is no evidence that the
phased mode runs a different BFS link algorithm. A claim that compiler
specialization directly sped up the inner BFS edge loop would be unsupported.
Different pre-loop execution/state can still affect that shared loop.

The runner also conditionally computes/stores durations before subsequent
phases. The observed constructor returns a graph plus timings, whereas the
whole constructor returns only the graph. Thus the treatment includes observer
logic, compilation/layout effects and state perturbation, not just time spent
inside `Instant::now`. Both branches use the same system-time implementation;
there is no evidence of different clock units or arithmetic underflow.

Reproduce the static inspection from the benchmark checkout without executing
the benchmark:

```sh
shasum -a 256 target/release/initialization-profile
xcrun llvm-nm --demangle --numeric-sort target/release/initialization-profile
xcrun llvm-objdump --disassemble --demangle --no-show-raw-insn \
  '--disassemble-symbols=initialization_profile::measure,<knotrel_benchmarks::engines::Engine>::new,<knotrel_benchmarks::engines::Engine>::new_with_timings' \
  target/release/initialization-profile
```

### Accounting versus validity

In the runner, `setup_other_ns` is defined as setup minus the named intervals.
The equality of their sum is consequently partly true **by construction**.
The checked subtraction is valuable for detecting overlap/overflow; tests also
check boundaries and graph semantics. But exact sums do not prove that a timer
measures only its named activity or that it does not perturb later work.

The maximum residuals, 0.1494% and 0.1420%, exclude clock/bookkeeping costs
already charged inside named intervals. They are not upper bounds on observer
overhead. Long scheduling stalls can also be correctly accounted elapsed time.
Nanosecond output does not imply nanosecond resolution or accuracy.

## 3. What the existing observations support

### Paired results

Percent changes are `100 * (phased / whole - 1)`, not ratios of group medians.

| Attempt | BFS median [bootstrap 95% CI] | ETT | HDT |
| --- | --- | --- | --- |
| First | +0.35% [-4.62%, +3.24%] | -0.70% [-5.34%, +4.54%] | -1.71% [-4.28%, +10.49%] |
| Replication | -9.53% [-22.94%, -2.04%] | +0.53% [-0.99%, +6.54%] | +2.73% [-2.31%, +34.96%] |

**Negative BFS result:** all six replication pairs favor phased, but the first
attempt does not reproduce that pattern. In the replication, whole setup spans
1.242-1.715 ms, versus 1.211-1.350 ms phased. The median phased non-edge time is
only 19.167 microseconds. Changes of hundreds of microseconds cannot be
explained as simple subtraction of that small phase's clock cost.

The replication's BFS median difference is -21.30% when whole runs first and
-5.70% when phased runs first (three pairs each). Both orders favor phased, so
a universal "second process is faster" explanation is insufficient; the much
larger whole-first difference nevertheless makes order/state important.
These post-hoc three-pair groups are descriptive, not independent significance
tests or permission to discard a group.

The saved macOS time-tool diagnostics add useful, limited evidence. For
replication BFS pair 4, whole versus phased:

- Setup: 1.715167 versus 1.349875 ms.
- Whole-process retired instructions: 60.004 versus 59.716 million.
- Whole-process cycles: 17.979 versus 17.974 million.
- Whole-process involuntary switches: 37 versus 13.

The nearly equal whole-process cycle totals alongside differing setup wall
times are compatible with scheduling/frequency/scope effects. They do not
identify one cause. Counters include startup, input preparation, destruction
and reporting; they must not be divided by setup time to infer frequency, IPC,
or per-edge cost.

**HDT variability:** the first phased process is exceptional in both attempts.

| Attempt | First phased setup | Following whole setup | Later same-mode setup medians: phased / whole |
| --- | ---: | ---: | ---: |
| First | 10.373500 ms | 8.645834 ms | 6.942 / 7.072 ms |
| Replication | 17.147500 ms | 10.738250 ms | 7.655 / 7.109 ms |

The last column is a diagnostic position comparison, not a revised estimate
excluding outliers. All first processes remain in the reported results.

The first process's `/usr/bin/time` **whole-process** real duration is 0.18 s
and 0.31 s, respectively, versus 0.01 s and 0.02 s for its partner. Recorded
in-process total initialization is only 12.267250 and 19.640167 ms for those
first phased runs. Most of the whole-process excess is therefore outside the
initialization interval, though that does not locate it within launch, loader,
teardown, reporting or descheduling. The time tool's coarse printed precision
precludes exact subtraction.

Both replication HDT partners have zero recorded major page faults/swaps and
almost identical page reclaims (2,260/2,259). This does not establish equal
allocator/cache state. The phased run's whole-process instructions are
136.738M versus 135.395M and cycles 59.011M versus 45.297M: much more cycle
variation than instruction variation, again not scoped enough for attribution.

### Environmental hypotheses and evidentiary limits

| Factor | Concrete evidence | What remains unproven |
| --- | --- | --- |
| Launch/session startup | First-process real-time excess repeats; same phased-HDT-first order repeats | Which launch/runtime/system activity caused it, or how much leaked into setup |
| Execution order | Fixed seed 42 reproduces the entire schedule; balanced three AB/three BA per backend | Balance does not eliminate nonlinear startup transients or time-varying interference |
| Allocator and memory state | Every process first generates/encodes the workload and drops its JSON bytes; then builds a temporary adapter map before graph registration | A fresh process is not a pristine allocator at setup. ASLR, reuse, page/cache placement and map cleanup effects are not measured separately |
| CPU scheduling | Saved whole-process involuntary switch counts; shared host, no recorded affinity/QoS policy | Switch timing/duration, run-queue delay and actual per-phase CPU assignment |
| Apple Silicon P/E cores | Same host currently reports four performance and six efficiency cores; manifests record only ten total CPUs | No core residency/migration trace exists. Do not label a slow run "E-core" from elapsed time or aggregate cycles |
| Thermal/frequency state | First build took 7.64 s; replication build reused artifacts in 0.14 s; lower replication load averages still accompanied failures | No per-run frequency, thermal state, power-mode or charging record; load averages are not thermal or core-frequency measurements |
| Compiler effects | Separate constructor bodies, stack footprints and specialized helper symbols confirmed; edge loop shared | Their causal contribution to the observed negative BFS difference |

`Instant` is an elapsed-time clock, not thread CPU time. P/E scheduling and
frequency can change work completed per unit wall time without making the
clock's arithmetic incorrect. Identical binary hashes rule out differing
executables between attempts, not differing execution state or branches.

The collector's three-second wait occurs once before the campaign. Between
children it writes JSON/stderr and rewrites a growing partial manifest. These
are outside setup but introduce uncontrolled gaps/system work. There are no
per-child monotonic launch/completion timestamps or per-phase scheduler
measurements. Reusing the same shuffled order in the replication preserves
rather than breaks its session-position confounding.

## 4. Assessment of the statistical gate

The old gate was a useful conservative **stop rule**, not an overhead estimator:
absolute median <=5%, percentile-bootstrap 95% CI inside +/-10%, residual <1%.
Stopping without removing observations was correct.

Its limitations are material:

- Six pairs give very little information about a skewed/heterogeneous
  distribution. Five thousand resamples reduce Monte Carlo error, not sampling
  uncertainty. A bootstrap cannot create unseen scheduling states.
- The bootstrap resamples six pairs as exchangeable observations, ignoring
  three-per-order stratification, temporal dependence and first-process status.
  Its nominal coverage is not established under those conditions.
- As a useful scale comparison, with six independent continuous observations
  the distribution-free interval `[min, max]` already has 96.875% coverage for
  the population median. There is little distribution-free precision available.
- A median confidence interval is not a bound on run-to-run spread or tails.
  A mode can pass despite substantial individual disturbances.
- Containing a 95% CI inside +/-10% resembles an equivalence rule at that wide
  margin, with an extra median gate. It does **not** establish equivalence
  within 5%, much less an overhead budget small relative to a future 5% gain.
- Slightly crossing +10%, as in the first HDT attempt, is not a scientific
  discontinuity. It means the predeclared screening rule was not satisfied.
  Conversely, ETT passing twice does not validate every backend or phase.
- There was no identical-path A/A control, so neither natural variability nor
  the instrumented treatment's incremental contribution is identifiable.

Keep the existing decisions unchanged. Do not pool these two attempts into a
new pass test or retrospectively optimize thresholds/order/outlier policy.

## 5. Revised protocol for approval

The following is a **bounded diagnostic protocol**, not authorization to
resume the full baseline or optimize graph construction. Numerical tolerances
are prospective engineering budgets relative to the intended 5% optimization
target, not universal statistical constants.

### Stage A: identical-path A/A using the existing executable

**Purpose:** quantify natural fresh-process variability without any mode change.

- Fixed cells: BFS, ETT, HDT; dense bridge n=512, seed=42, rounds=1,
  adapter surface, **whole mode in every child**, warmup=0, repetitions=1,
  no dynamic validation. Retain the existing phase/timer definitions.
- A and A' labels exist **only in collector metadata**. Child executable,
  argv, environment, working directory, input and stdout handling are identical.
  Do not pass a distinguishing label flag/environment variable to the child.
- 24 adjacent pairs per backend, divided into three sessions of eight pairs
  per backend: **144 measured processes**, fixed before launch.
- Separate sessions by a fixed five-minute quiet interval; before each session
  allow 60 seconds with no user-initiated build/test/workload. Use AC power and
  unchanged power mode/QoS. Do not kill system/security services. If an exclusive
  host is unavailable, disclose that limitation rather than claim isolation.
- Rotate pair-level engine order B/E/H, E/H/B, H/B/E across rounds and session
  starts; each engine starts one session. Within each backend/session assign
  four A/A' and four A'/A metadata orientations using fixed seeds
  120047, 120048, 120049. Archive the actual complete schedule before collection.
- Keep every first process. No throwaway graph priming, cache flushing,
  selective warmup or adaptive waiting. "Fresh" does not mean cold caches.
- Record monotonic parent launch/completion timestamps, session/pair/serial
  position, raw process diagnostics, configuration/power metadata available
  without privileged intrusive tracing, source/binary hashes and all errors.
  Buffer collector records between the two children; write them after the pair.
  On failure, flush the partial pair and stop. Do not analyze results between
  pairs or overlap collection with compilation, tests or disassembly.

Report **both** labeled log ratios `d = log(t_A'/t_A)` and chronological
`log(t_second/t_first)`, so random labels cannot conceal order effects.
Setup is the primary metric; apply the same validity gates to total
initialization if it is to be used as a trustworthy reported total.

For each backend and metric:

1. Retain all 24 paired differences, medians, IQR, min/max, `median(abs(d))`,
   tail counts, session summaries and chronological position effects.
2. Use the distribution-free median interval from sorted differences
   `[d_(7), d_(18)]`: 97.7344% coverage for 24 independent continuous pairs.
   Express results as `100*(exp(d)-1)`. The coverage claim is conditional on
   independent/exchangeable pairs; it is not a cure for temporal dependence.
3. Require this interval within `[-log(1.02), +log(1.02)]`.
   Also require `median(abs(d)) <= log(1.03)` and at most two of 24 absolute
   differences exceeding `log(1.10)`. The last rule is an empirical tail gate,
   not a population-tail confidence bound.
4. Require each eight-pair session's labeled median within +/-log(1.03), and
   each session's chronological second/first median within +/-log(1.03).
5. For each backend/session, compare its first observation with the median of
   its remaining 15 observations. A ratio outside `[1/1.10, 1.10]` flags a
   startup-sensitive session and fails the gate; do not remove that observation.
   Plot full order trends as diagnostics. These finite checks still cannot
   prove independence, so disclose remaining dependence risks.

These thresholds may yield an inconclusive result; 24 pairs are a bounded
diagnostic budget, **not a claimed power calculation**. Failure means stop and
request a new design/host decision, not add pairs until the interval narrows.
These dense cells do not certify sparse registration-heavy workloads.

### Stage B: separate scaffolding from boundary instrumentation

Only after Stage A passes, and after approval to implement this diagnostic:

1. Retain an **U** reference whole path in one new release artifact.
2. Provide **N**, a common, non-generic construction path with runtime
   no-op boundary observation.
3. Provide **T**, the **same** compiled path and boundary points, now reading
   timestamps into fixed preallocated storage. No allocation/logging in the
   observer. Compute duration fields after the final enclosing timestamp.
4. Preserve input generation, JSON preparation/disposal, node registration
   order, temporary-map lifetime, edge order, return semantics, and the
   existing conceptual phase boundaries. Do not move validation or cleanup
   out of setup, omit input work, or add per-edge clocks.
5. Inspect the produced binary before running it: N/T must execute the same
   graph-work basic blocks/call targets, differing only in observer branches.
   A no-inline annotation or source-level helper is not proof; rule out
   compiler cloning/specialization by inspection. If this cannot be established,
   report only total implementation perturbation, not isolated observer cost.

U/N measures scaffolding/common-path changes; T/N measures **net boundary
instrumentation perturbation**; T/U measures the combined effect. None should
be called a pure hardware clock-call latency or used for overhead subtraction
from production timings.

For each dense backend, run 24 randomized balanced **quartets U, N1, N2, T**,
three sessions of eight: **288 measured processes**. N1 and N2 are identical
child invocations, labeled only externally. This embeds a fresh A/A control for
the new binary; the old artifact's A/A results do not certify the new one.
Use balanced four-position orders, each label occurring twice in each position
per eight-quartet session; archive the fixed order using seeds
120050, 120051, 120052 before collection. Rotate engine/session starts as in A.

Per quartet, use the geometric mean of N1/N2 as N, and report log ratios T/N,
N/U, and T/U. Apply the 24-observation exact median interval above, separately
per backend, requiring **all three** inside +/-log(1.02), and the Stage-A
stability gates for N1/N2. Inspect session/order effects, not only aggregate
ratios; apply the same first-observation startup flag separately to each mode's
session observations. A negative difference outside the tolerance is a perturbation signal,
not evidence that clocks are free.

In each session, permit one separately labeled, fixed 10,000-iteration
preallocated boundary-only probe **after** graph collection (three extra
processes total). It characterizes clock/store/bookkeeping scale, not graph
overhead. Do not subtract it. Mark a named phase too short for attribution if
its median is less than 20 times the probe's p95 cost of that phase's boundary
pair; this is a conservative reporting floor, not a proof of <5% error.

Stage B's maximum is therefore **291 processes**; the whole proposed diagnostic
has a hard maximum of **435**, gated after A. No baseline/limits matrix is
automatically added. A future baseline needs controls covering its other
topologies/scales and any facade path, under separate approval.

### Errors, stopping, and interpretation

- Integrity/accounting/correctness failure, timeout, changed binary/source/input,
  known concurrent user workload, sleep/power-mode transition, or inability to
  establish required path identity: preserve all records and stop.
- Statistical gates are evaluated once at each completed fixed stage; no
  deletion of slow samples, opportunistic retry, optional stopping, or widening
  the acceptable interval after seeing results.
- If a host event occurs, mark the session compromised rather than silently
  replacing it. Its interpretation and any new session require approval.
- No isolated P/E-core, frequency, thermal, allocation, or AVL causal claim
  without appropriate scoped evidence. If these remain unobserved, report
  wall-time variability and uncertainty, not a guessed mechanism.
- Preserve fresh build-only whole-process RSS, but do not infer phase memory or
  subtract process peaks. Any diagnostic with deliberate in-process warmup is
  a different protocol and must not be pooled with this one.

## 6. Recommendation

Approve **Stage A first**, not another whole-versus-phased calibration. It can
use the existing executable with no graph or timing-path change and answers
the missing question: how variable are two runs of exactly the same path?

If A is stable, the proposed Stage B can determine whether the current split
constructor/observer design introduces material perturbation. If A is unstable,
source optimization or more clock instrumentation is not the appropriate next
step. Resolve the execution environment/protocol first.

Dense edge insertion remains the dominant observed setup interval, but the
existing evidence cannot rank repeated lookups, allocation, B-tree incidence
work and AVL maintenance. It supports neither a library replacement nor direct
forest construction yet. No further collection or implementation has been
performed as part of this review.
