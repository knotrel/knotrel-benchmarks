# M6.5 metrics overhead on the v0.4.0 RC, run 1 (procedural deviation)

**Status: retained evidence with a documented procedural deviation. Not the
definitive G7-V qualification.** The owner retained this campaign unchanged
and authorized one complete repeat to correct the deviation:
[`metrics-overhead-rc-62c2cea-r2`](../metrics-overhead-rc-62c2cea-r2/README.md).
Both outcomes are reported. The repeat is the one evaluated under the
approved rules; it was not chosen for its result.

Generated tables: [REPORT.md](REPORT.md). Plan: knotrel
`docs/release-v0.4.0-qualification-plan.md` §7 (decisions G7-V, G7p-1).

## Identity

| Item | Value |
|---|---|
| Measured tree | knotrel `62c2cea9314085f6f7669ebbb7def2be1fa1cb5c`, clean (identity `e3b0c442…`, empty code diff) |
| Tools | knotrel-benchmarks `15a0f78582aa43b3101dbd766badc07ed295cfce` |
| Probe | `tools/hot-path-probes-rc` (`Cargo.toml` `1c5076bb…`, `Cargo.lock` `344d3c49…`), the shipped server's `axum` features |
| `router-probe` sha256 | `2e1cadd4dc135b39e570887804dc2a409e2306eb0824e444e9807369b99183b0`, one file for `on` and `off`; `aa` a byte-identical copy |
| Command | `python3 scripts/run_metrics_overhead.py results/metrics-overhead-rc-62c2cea --measured-commit 62c2cea9314085f6f7669ebbb7def2be1fa1cb5c`, host checks enforced |
| Collection | 2026-11-15 18:13:25–18:19:01 UTC, 335.9 s, 74 observations, no extension |

## Results

Budget, approved before M6.5 and unchanged: PASS if the paired median ≤ 3%
and the 95% interval's upper bound ≤ 6%.

| Scenario | on vs off [95% CI] | A/A bound | Verdict |
|---|---|---|---|
| `batch_1024_connected` | +1.24% [+0.27%, +3.29%] | ±1.62% | PASS |
| `batch_1024_cut_link` | +1.88% [+0.96%, +2.85%] | ±0.85% | PASS |
| `concurrent8_single_connected` | +0.43% [−1.29%, +2.06%] | ±1.31% | PASS |
| `feeder_events_1024` | +0.78% [−0.64%, +2.01%] | ±0.95% | PASS |
| `import_100000_chain` | +0.34% [−4.51%, +5.38%] | ±4.25% | PASS |
| `single_connected` | −11.01% [−12.44%, −7.19%] | ±1.76% | PASS |

**Checks, all passed:**
- **Observations:** 74, no failure or timeout, every stream hash matches.
- **Identity:** unchanged after the build and at the end.
- **Host:** all 25 host checks valid, with AC power, no thermal warning and
  no competing build.
- **Analysis:** `analyze.py --check` regenerates the outputs identically.

## Deviations

1. **Agent activity during the run.** The agent ran nine short read-only
   shell commands between 18:13:30 and 18:14:25 UTC, reconstructed from the
   session transcript. They were `ls`, `cat`, `grep`, `git show` and JSON
   reads of other evidence directories and scripts, each about 1 s. No cargo
   or rustc was run.
   - **During the untimed probe build** (18:13:26–18:13:47): four commands.
   - **During the 60 s pre-session quiet period** (18:13:47–18:14:47): five
     commands. The period was therefore not idle for its first 38 s.
   - **During timed observations:** none. The last command ended 22 s before
     round 1.
   - **What was checked:** the protocol's enforced host checks all passed.
     The early rounds show no visible departure: `batch_1024_cut_link`
     rounds 1–2 are +0.96% and +1.84%, against a median of +1.95% over the
     rest.
   - **Not concluded:** the deviation is not declared harmless, nor
     invalidating. It is corrected by the repeat.
2. **Host background load higher than in M6.5.** The 1-minute load average
   had a median of 2.68 (range 2.2–3.7), against 1.63 in M6.5, throughout the
   run.
   - The top processes were interactive applications, each under 3.2% CPU.
   - This is within the protocol's host checks, which do not bound load
     average.

## Limits

- **Scope:** in-process router probe, no sockets, no tracing subscriber.
  Disabled log callsites take the same path in every arm. One host (Apple
  M3, macOS), Rust 1.100.0.
- **`single_connected` is faster with metrics on, as it was in M6.5
  (−12.9%).**
  - **Cause not established.** No code path is known to explain a speedup
    from enabling metrics.
  - **A hypothesis, not evidence:** the M6.5 README suggests start-up
    effects, because this scenario runs first in each process. No causal
    test of it exists.
  - **The recurrence is not proof:** that the result recurs does not by
    itself show that it is an artifact.
  - **No speedup claim:** the verdict only bounds slowdowns. No claim of
    speedup is made, and no threshold is changed.
