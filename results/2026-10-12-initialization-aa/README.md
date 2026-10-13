# Stage A identical-path initialization: stability gates failed

**Decision: stop.** All **144 observations / 72 pairs** completed, with exactly
24 pairs per backend across three counterbalanced sessions. Preflight and
monitored integrity/host conditions passed, but **BFS, ETT and HDT each failed
the approved stability criteria**. This host/procedure is not validated for
the planned precision of the Phase-0 study. No observations were excluded,
replaced or repeated. No instrumentation-overhead experiment, topology
campaign, bulk loading or graph-algorithm change was performed.

## Protocol and implementation

The [approved methodology](approved-methodology.md) was frozen before
collection; its statistical criteria, sample count, order and stopping rules
were unchanged. The new [collector](../../scripts/run_initialization_aa.py)
implements only Stage A. Its [tests](../../scripts/tests/test_initialization_aa.py)
cover schedule/argument identity, fixed gates, startup handling, partial-stage
rejection, pair buffering and immediate preflight/child-failure stopping.
The targeted suite passed **14 tests**, including three existing initialization
tests; Pylance reported no syntax errors in either new Python file.
No Rust source was changed or executable rebuilt for this stage.

- Apple M4, 16 GiB, four Performance and six Efficiency cores; macOS 27.0.1
  arm64. Existing reviewed release executable, not a new compilation.
- Dense bridge, 512 vertices, 65,281 initial edges, seed 42, one generated round.
  Adapter surface, **whole mode for every child**, warmup 0, repetitions 1,
  no dynamic validation/replay.
- Three sessions, eight pairs/backend/session. Engine starts were BFS, ETT,
  HDT respectively; round order rotated cyclically. Seeds 120047/120048/120049
  assigned four A/A-prime and four A-prime/A orientations per backend/session.
- Both children used identical executable, argv, inherited environment, working
  directory and output handling. Labels existed only in parent metadata.
  This removes the earlier whole-versus-phased compiled-constructor comparison:
  both labels select the same whole-mode implementation.
- Complete [schedule](schedule.json) and [preflight provenance](preflight.json)
  were archived before the first child. Full hashes were checked around pairs;
  binary file identity was also checked before each child.
- Fixed quiet waits measured **60.083, 300.096 and 300.099 seconds**. Each
  five-minute gap includes the next session's final 60 quiet seconds; waits
  were not adapted to timing results. The small excess is wait/check overhead.
- Records stayed in memory between successful children; raw files were written
  after each pair. No builds, tests, disassembly or statistical analysis ran
  concurrently with collection. All first observations were retained.
- Total collector elapsed time, including quiet waits: **674.284 seconds**.
  Statistical criteria were evaluated only after all 144 observations; exit
  status 1 indicates the preserved statistical failure, not a child failure.

Identity anchors:

| Item | Recorded identity |
| --- | --- |
| Core revision, clean | `61a3556435f10ec9d5fe768682f1195ebd22ac71` |
| Benchmark base revision, existing dirty tree recorded | `1567a4e2adee8f3e35eae9923107505868b3f01d` |
| Executable SHA-256 | `9992c7104ac1b6875aebe1a18d024b266feae55f48d513dfc893b3e71fe99fc5` |
| Approved methodology SHA-256 | `446490ed560dbfa04e8c92920734ec70572fddde0b1aea5521d5849f9220dff6` |
| Final manifest SHA-256 (after [path normalization](../2026-10-13-path-normalization/README.md)) | `9ffcd03e2da693c9b2e790c9282d7c18130799e602537339f74f9a537119f99e` |
| Final manifest SHA-256 as collected, before normalization | `64ac6e2be1b45fd63221ef7e836bfcdde1651bdb2cc9739ff85929d7420fe715` |
| Trace fingerprint, every child | `b4768a77d485a99f` |

Rust/build-input hashes match both previous calibration manifests. Post-run
verification checked all **375 manifest-listed artifacts**, the 144 raw reports
against manifest records, identical pair argv/environment hashes, the complete
actual order and non-overlapping launches, and fixed wait durations. It also
rechecked all **82 listed artifacts in each previous calibration** unchanged.
The core remained clean. The report is a later addition, not a replacement for
any manifest-listed evidence. Machine-local absolute paths in the recorded
commands were later replaced by placeholders and the dependent hashes were
recomputed; the measurements and statistics are unchanged (see the
[normalization record](../2026-10-13-path-normalization/README.md)).

## Fixed statistical results

Setup is the primary node-vector-to-loaded-graph interval. Total initialization
also includes preceding input preparation, as defined by the existing runner.
Both are unchanged whole-mode wall-clock measurements; no internal phase
durations or instrumentation overhead are estimated here.

For each metric, `d = log(t_Aprime / t_A)`. Percentage summaries transform log
statistics as `100 * (exp(d) - 1)`, including the median and interval. The exact
median interval uses ranks **7 and 18 of 24**, with **97.7344%** coverage under
the independent continuous-pair assumptions, not a bootstrap interval.
Acceptance requires the interval inside `+/-log(1.02)`, median absolute log
difference at most `log(1.03)`, and at most two tails beyond `+/-log(1.10)`.
These correspond to interval endpoints **[-1.9608%, +2.0000%]**, variability
at most 3%, and ratios outside **[0.9091, 1.1000]** for tail counting.

| Backend | Metric | Median paired change | Exact median interval | Multiplicative median absolute difference | Tails / 24 |
| --- | --- | ---: | ---: | ---: | ---: |
| BFS | Setup | -1.43% | [-5.14%, +1.60%] | 3.59% | 9 |
| BFS | Total | -0.43% | [-3.87%, +7.17%] | 6.64% | 8 |
| ETT | Setup | +0.42% | [-1.95%, +1.37%] | 1.96% | 3 |
| ETT | Total | -0.11% | [-1.70%, +1.59%] | 1.70% | 1 |
| HDT | Setup | -0.77% | [-2.36%, +4.75%] | 3.15% | 7 |
| HDT | Total | -0.17% | [-2.72%, +5.02%] | 4.94% | 6 |

BFS and HDT fail all three aggregate criteria for both metrics. ETT setup
passes precision/median variability but fails the tail criterion. **ETT total
passes all three aggregate criteria but still fails startup**, so it is not
an accepted result.

All session gates were also applied: each labeled and chronological
second/first median must be within `+/-log(1.03)`, and first observation divided
by the median of the remaining 15 must be in **[0.9091, 1.1000]**.
Session numbers below are zero-based, matching the artifacts.

| Backend / metric | Failed session median gates | Failed startup ratios |
| --- | --- | --- |
| BFS / setup | S0 labeled -4.74% | None |
| BFS / total | S1 labeled +7.55%, chronological -7.02%; S2 labeled -3.35%, chronological +3.47% | None |
| ETT / setup | None | S0: 1.22984 |
| ETT / total | None | S0: 1.23020 |
| HDT / setup | S1 chronological -10.66% | S1: 1.11548 |
| HDT / total | S1 chronological -10.00%; S2 chronological -4.72% | S1: 1.10621 |

All other session/startup checks passed. Full passing and failing ratios,
individual pairs and chronological distributions are in [analysis.json](analysis.json);
the [full-order plot](order.svg) retains every observation.
The exact ranks, absolute-difference/tail gates and session/startup checks were
also independently recomputed from the recorded observations after collection.

## Descriptive distributions, not a certified baseline

Each duration distribution contains 48 observations. Units are milliseconds.
Do not interpret differences between labeled identical children as speedups.

| Backend / metric | Median [Q1, Q3] | Min-max | Paired change Q1-Q3 | Paired change min-max |
| --- | ---: | ---: | ---: | ---: |
| BFS / setup | 1.241 [1.228, 1.298] | 1.199-1.634 | -5.60% to +1.67% | -18.07% to +31.77% |
| BFS / total | 2.404 [2.349, 2.521] | 2.309-2.918 | -4.09% to +7.36% | -11.48% to +21.69% |
| ETT / setup | 5.023 [4.849, 5.137] | 4.558-5.967 | -2.36% to +1.51% | -10.40% to +16.89% |
| ETT / total | 6.169 [5.957, 6.273] | 5.664-7.325 | -2.18% to +1.61% | -8.28% to +14.35% |
| HDT / setup | 7.207 [6.838, 7.734] | 6.315-8.512 | -2.37% to +5.06% | -17.62% to +21.14% |
| HDT / total | 8.373 [7.981, 8.942] | 7.486-9.691 | -3.07% to +5.22% | -16.24% to +20.33% |

Setup tail-pair IDs, retained without exclusions: BFS
`0, 14, 18, 30, 44, 56, 58, 65, 69`; ETT `1, 10, 38`;
HDT `6, 25, 32, 34, 41, 43, 64`. These IDs resolve to the
corresponding pair files, for example [pair-00.json](pair-00.json).
Total-metric tails and every individual ratio remain in the analysis.

Whole-process peak RSS comes from raw `/usr/bin/time -l` diagnostics. It
includes runtime, input/JSON, graph, allocator and reporting; it is **not**
engine heap or phase-specific peak memory.

| Backend | Peak RSS median [Q1, Q3], MiB | Peak RSS range, MiB |
| --- | ---: | ---: |
| BFS | 5.2188 [5.2031, 5.2188] | 5.2031-5.2344 |
| ETT | 16.4062 [16.4062, 16.4219] | 16.4062-16.4375 |
| HDT | 32.5156 [32.5000, 32.5156] | 32.4844-32.5469 |

All process records include wrapper PID, monotonic launch/completion times,
exit status, RSS, page-fault/reclaim/swap counts, context switches and available
whole-process instruction/cycle diagnostics. No IPC/frequency/phase-work
inference is made from these unscoped counters. Printed process `real` times
are only hundredth-second resolution (BFS printed 0.00 throughout), unsuitable
for replacing the internal timers. Parent-observed wrapper lifetimes had
medians **10.853 / 15.584 / 18.125 ms** for BFS/ETT/HDT; these include launch,
wrapper and collection overhead, not just initialization.

## Host observations and interpretation

The **215 recorded host snapshots** reported AC power, battery charged 100%,
unchanged low-power mode 0, unchanged sleep/wake records and collector nice 0.
No recognized concurrent build/test/benchmark process was detected. The
user-authorized temporary idle-sleep assertion stayed active during collection
and was terminated/reaped on exit; no power-mode/QoS change was requested.
One-minute load averages ranged **2.470-4.962**. The host was shared, with
runtime/editor/background services present; these are not isolation guarantees.

Thermal queries succeeded but reported **no recorded thermal/performance warning
or CPU power status**. That is not a measured stable temperature or frequency.
Core residency, actual QoS class, DVFS, per-child allocator state and scheduler
decisions were not observed. Sampling host state around pairs can miss short
events. `MallocNanoZone=0` was inherited identically by every child, not changed
for this experiment. Other benign configuration values and the full environment
hash are retained; complete environment values were not persisted.

The strongest directly supported findings are:

1. **Substantial variability exists without switching timer configurations.**
   BFS setup paired changes span -18.07% to +31.77% under identical invocations.
   This makes natural procedure variability a credible contributor to earlier
   negative BFS differences; it does not identify the cause of those campaigns.
2. **Label balancing does not eliminate chronological effects.** HDT's aggregate
   labeled medians are near zero, but S1 second/first medians are -10.66% setup
   and -10.00% total. Its setup session medians also drift from 6.826 to 7.163
   to 7.710 ms. Treat this as order/time sensitivity, not an algorithm change.
3. **Quiet waits did not eliminate first-observation sensitivity.** ETT S0's
   first observation was about 23% above its remaining-session median for
   both metrics; HDT S1 also failed startup. None was discarded.
4. **The procedure has asymmetric spacing.** Median parent-observed gaps were
   0.174 ms within pairs versus 149.672 ms between pairs within sessions
   (ranges 0.109-0.423 and 138.352-195.510 ms). Between-pair provenance checks,
   host probes and writes are outside the measured graph interval, but may
   affect subsequent host/cache state. This is a plausible contributor, not
   a demonstrated mechanism or grounds to revise the protocol retrospectively.

Identical binary/arguments establish the same selected compiled implementation,
not identical addresses, allocator outcomes, dynamic instruction traces or CPU
conditions. This A/A measures natural variability of the complete prescribed
procedure; it cannot isolate clock overhead or assign causality to P/E cores,
thermal changes, allocation or any graph primitive.

## Reproduction and stopping decision

[manifest.json](manifest.json) indexes observations, hashes and configuration.
Each numbered child JSON has matching raw stderr; pair files record surrounding
host snapshots. The collector/helpers/tests are archived under
[collector/](collector/). The three session files retain quiet-wait checks.
The previous calibrations remain separate and were not pooled with this stage.

From the benchmark repository root, this **offline check launches no benchmark**:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 - <<'PY'
import hashlib
import json
from pathlib import Path
import sys

root = Path("results/2026-10-12-initialization-aa")
sys.path.insert(0, str(root / "collector"))
import run_initialization_aa as aa

manifest = json.loads((root / "manifest.json").read_text())
for name, expected in manifest["artifact_sha256"].items():
    assert hashlib.sha256((root / name).read_bytes()).hexdigest() == expected, name
assert aa.analyze(manifest["observations"]) == json.loads((root / "analysis.json").read_text())
print(manifest["status"], len(manifest["observations"]))
PY
```

The collection command was:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 scripts/run_initialization_aa.py \
  results/2026-10-12-initialization-aa --prevent-idle-sleep
```

This destination cannot be reused. The command documents provenance, **not
authorization for another collection**.

**Recommendation:** do not proceed to Stage B or claim a trustworthy Phase-0
baseline. Precision/tail/session/startup failures remain after the fixed bounded
A/A budget. A new host/procedure decision requires separate approval; do not
increase the sample count, warm away first observations, relax gates or
reinterpret ETT's aggregate pass as an overall pass.

The exact interval's coverage remains conditional on independent continuous
pairs, and the session/order findings give reasons for caution about dependence.
The 24-pair budget was diagnostic, not a power calculation; failure does not
prove that reliable measurement is impossible on this hardware. Even a pass
would certify neither instrumentation overhead nor sparse/registration-heavy
workloads. No Stage-B implementation or collection is authorized by this result.
