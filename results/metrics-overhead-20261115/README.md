# M6.5 Metrics Overhead Qualification (knotrel v0.4.0 candidate)

Hand-written narrative. All numbers come from the generated
[REPORT.md](REPORT.md) and [analysis/summary.json](analysis/summary.json),
regenerated from [run/](run/) by [analyze.py](analyze.py). If they disagree,
the generated files win.

## Purpose

Roadmap M6.5 requires the instrumentation overhead of the opt-in Prometheus
metrics to be verified against a budget approved before measurement
(knotrel `docs/observability-contract.md`, sections 6 and 9). This campaign
measures `KNOTREL_METRICS_ENABLED` on versus off on the in-process
`knotrel-server` router of the v0.4.0 candidate tree.

**Budget (approved by the owner on 2026-11-15, before measurement).** Per
scenario: paired median slowdown at most 3% and upper bound of its 95%
interval at most 6% → PASS; interval lower bound above 3% and median above
the A/A bound → REGRESSION (blocks Acceptance M6); otherwise INCONCLUSIVE. One
fixed extension of 12 rounds only if a scenario is not PASS after the primary
24 rounds.

## Outcome

**6 PASS, 0 INCONCLUSIVE, 0 REGRESSION** after the 24 primary rounds; no
extension ran. Paired change of metrics on versus off:

| Scenario | Change [95% CI] | A/A bound |
| --- | ---: | ---: |
| Single `connected` | −12.92% [−14.09%, −9.08%] | ±4.28% |
| 8 concurrent clients, single `connected` | +0.73% [−0.26%, +1.58%] | ±1.53% |
| Batch, 1,024 `connected` | +1.28% [+0.60%, +1.59%] | ±0.65% |
| Batch, 1,024 alternating cut/link | +0.99% [+0.46%, +1.93%] | ±1.33% |
| Import, 100,000 nodes | −0.64% [−3.25%, +0.57%] | ±3.64% |
| Feeder batch, 1,024 events | +0.60% [−0.30%, +1.82%] | ±1.47% |

The largest measured cost is the batch of 1,024 `connected` queries, +1.28%
(interval upper bound +1.59%), well inside the budget.

**Single `connected` anomaly.** The metrics-on arm is faster for the first
scenario of each process. No code path explains a speedup from enabling
metrics. The single-request scenario runs first in every process and lasts
about 14 ms, so it is the most exposed to start-up effects (CPU frequency
ramp, cache and page warm-up); enabling metrics performs registry
construction before it, which plausibly changes that warm-up. The hot-path
audit campaign showed the same direction (unpaired). This is **not** a
speedup claim: the budget verdict only bounds slowdowns, and this row says
only that no slowdown beyond the budget was observed.

## Identity

| Item | Value |
| --- | --- |
| knotrel base commit | `e1e11818a762baf07575719456a2158959b2e2c8` (`refactor/typed-constants`) |
| Measured tree identity | `6ec5f564d34255b8be3aab782d7edff12fc3008415c29fe871ad07d93ae65c3c` |
| Code diff (`git diff HEAD -- . ':(exclude)docs' ':(exclude)*.md'`) | `29657de657abd8a1a3148242f6baee22f8b6c24128f03815a67fc660328bd522` |
| Untracked code files included | `crates/knotrel-server/src/logging.rs`, `crates/knotrel-server/tests/logs.rs`, `examples/observability/prometheus-alerts.yml` |
| `router-probe` sha256 (all arms) | `c8b5cff5325865435f6d3f8e21dacb42ebbcaa320435e9271eff17bd666afeb6` |
| Toolchain / host | Rust 1.100.0; Apple M3, macOS 26.5.2, AC power |
| Collected | 2026-11-15, 09:58–10:03 UTC, 74 observations |

The identity is the sha256 of the code diff together with each untracked code
file's path and hash. The collector checked it before the build, after the
build and after the last observation; it never changed. The patch and the
untracked files are archived in [run/tree/](run/tree/), so the measured tree
is `git archive e1e1181` + `git apply run/tree/code.patch` + `run/tree/untracked/`.
The tree includes the hot-path changes, M6.2 review fixes and M6.3 logging,
i.e. the v0.4.0 candidate code.

## Method

- One release build of `tools/hot-path-probes` `router-probe` (mimalloc,
  like the server) linked against the knotrel working tree. Arms: `off`
  (binary without `--metrics`), `on` (same binary with `--metrics`), `aa`
  (byte-identical copy under another path, without `--metrics`).
- `router-probe --mode timing --iterations 2000`: the six scenarios through
  the full Axum router via `tower::ServiceExt`, no sockets; see
  [tools/hot-path-probes/README.md](../../tools/hot-path-probes/README.md).
- 24 counterbalanced rounds in two sessions (every arm order four times),
  60 s quiet before, 120 s between sessions, 5 s between rounds; host checks
  enforced (AC power, no competing builds, no thermal warning).
- Per round, percent change of `on` and `aa` against `off`; paired median and
  95% percentile bootstrap interval (10,000 resamples, seed 20261115).
- A `verify` pass of both arms ran first (response digests archived).

## Caveats

- **Logs are not measured here.** The probe installs no tracing subscriber,
  so log statements are disabled in every arm. The cost of M6.3 logging at
  the default `info` filter is covered by the v0.4.0 regression
  qualification against v0.3.0 (roadmap 0.4.2.3), which runs the real server.
- **In-process only.** No sockets: the relative cost is larger than over
  TCP, where connection handling dilutes it.
- **Series count** is qualified by tests, not by this campaign:
  `series_count_is_constant_under_sustained_churn` in knotrel
  `crates/knotrel-server/tests/metrics.rs` (20 cycles of session takeovers,
  replacement imports, desynchronizations, rejections and fresh node IDs; the
  count is constant after the first full cycle and below the calculated
  maximum of 1,834).
- One host; six scenarios without family-wise correction (each verdict is a
  budget decision, not a significance test).

## Reproduction

From `knotrel-benchmarks`, with the knotrel candidate in the sibling checkout:

```sh
python3 scripts/run_metrics_overhead.py <new-campaign-directory>
```

Regenerate and check this campaign's derived files:

```sh
python3 results/metrics-overhead-20261115/analyze.py
python3 results/metrics-overhead-20261115/analyze.py --check
```

Collector tests: `python3 -m unittest discover -s scripts/tests -p test_metrics_overhead.py`.
