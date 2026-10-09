# Investigation: 100k path / 50% query regression

## Finding

The previously reported **11.62% warmed regression is not stable across sessions**.
It was a measured four-trial median, not proof of a persistent slowdown or a
causal diagnosis. In this fixed follow-up, 12 new paired trials per regime
(48 processes) yield lower after-runtime medians in both regimes. Do not erase
or pool the earlier unfavorable observations. No production code was changed.

Both original frozen executables are reused with verified binary hashes, exact
reference arguments (100k vertices, path, 50% queries, 10 rounds, seed 42), and
alternating adjacent before/after order. Trial order is shuffled with seed 42.
Fresh and warmed mean harness warmup 0 and 1, not cache flushing. Cases validate
exact answers and fingerprints. All paired HDT work counters match, with zero
tree promotions. Source hashes and build snapshots remain in the manifest.

## Evidence across collections

| Collection | Trials per regime | Fresh runtime delta | Warmed runtime delta |
|---|---:|---:|---:|
| Initial direct-join matrix | 2 | +50.42% | +25.34% |
| Adaptive regression confirmation | 4 | −18.85% | +11.62% |
| This fixed investigation | 12 | −11.30% | −8.98% |

Delta is `100 * (median(after) / median(before) - 1)`. Negative means lower
runtime. These are separate collections, not independent guarantees of speedup.
The adaptive collection selected initially unfavorable cells; this investigation
was fixed to one scenario and both cache regimes before collecting new data.

| Regime | Replay delta | Cut total delta | Query total delta | Link total delta | Setup delta |
|---|---:|---:|---:|---:|---:|
| fresh | -11.30% | -12.98% | -10.21% | -8.79% | -37.27% |
| warmed | -8.98% | -10.22% | -6.41% | -16.73% | -36.89% |

The original warmed confirmation had cut total +9.76%, query total +16.18%,
but link total −9.90%. Thus it did not show the changed link operation becoming
slower. Setup improves consistently by roughly 36–37%; setup is excluded from
replay time. A different initial tree layout could still affect subsequent cuts
or queries; this probe does not directly measure tree depth or CPU cache misses.

| Regime | After slower pairs | Median paired delta | Paired delta range |
|---|---:|---:|---:|
| fresh | 1/12 | -8.67% | -39.25% to +3.63% |
| warmed | 5/12 | -4.31% | -24.26% to +69.86% |

Median paired ratios differ from ratios of medians: both are shown deliberately.
In particular, the warmed sample includes an after-slower pair near +70% despite
its lower aggregate median. Process variability is large relative to the earlier
11.62% difference. No scheduling, thermal or hardware-counter measurements were
collected, so attributing the variation specifically to caches, throttling or
OS scheduling would be speculation. The experiment does not isolate a stable
algorithmic regression or prove its absence under all conditions.

## Decision

Keep the direct-join implementation experimental and retain all three sets of
results. No speculative rollback, special-case path handling or new configuration
is justified by this probe. The earlier wording “confirmed regression” should
be read as “observed again in four trials”; this investigation supersedes any
claim that the 11.62% magnitude is stable.

If investigation continues, the next discriminating measurement is deterministic
structural work (root/rank traversal steps and split/join/pull counts) on the
same trace, with instrumentation excluded from normal timing results. That can
separate tree-layout effects from elapsed-time variability. More short timings
alone will not establish that cause.

## Reproduction and checks

Run `collect.py` only in a fresh output directory using the existing pinned
before/after executables at `/private/tmp/knotrel-hdt-joins`. Then run `compare.py`
and `analyze.py`. `comparison.json` retains per-process ranges, operation tails,
RSS and historical drift; `analysis.json` retains paired deltas and hash audits.
All 48 processes succeeded; exact fingerprints and work counters match. Hashes
of this collection and both preceding collections were verified. Core and server
source were unchanged, so correctness suites were not rerun for this data-only
investigation. Whole-process RSS is not engine heap usage.
