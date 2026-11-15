# M6.5 metrics overhead on the v0.4.0 RC, run 2 (G7-V repeat)

**Status: the G7-V campaign evaluated under the approved rules.** It is the
single complete repeat the owner authorized, to correct the procedural
deviation of run 1. That run is
[`metrics-overhead-rc-62c2cea`](../metrics-overhead-rc-62c2cea/README.md),
retained unchanged.
- **Unchanged from run 1:** the sources, binary, configuration, criteria and
  budget. The protocol was not changed after run 1's results.
- **Both outcomes are reported:** below and in run 1's README.

Generated tables: [REPORT.md](REPORT.md). Plan: knotrel
`docs/release-v0.4.0-qualification-plan.md` §7 (decisions G7-V, G7p-1).

## Identity

| Item | Value |
|---|---|
| Measured tree | knotrel `62c2cea9314085f6f7669ebbb7def2be1fa1cb5c`, clean (identity `e3b0c442…`, empty code diff) |
| Tools | knotrel-benchmarks `15a0f78582aa43b3101dbd766badc07ed295cfce`; `analyze.py` byte-identical to run 1's committed copy |
| Probe | `tools/hot-path-probes-rc` (`Cargo.toml` `1c5076bb…`, `Cargo.lock` `344d3c49…`), the shipped server's `axum` features |
| `router-probe` sha256 | `2e1cadd4dc135b39e570887804dc2a409e2306eb0824e444e9807369b99183b0`, identical to run 1 (cargo found the build fresh). One file for `on` and `off`; `aa` a byte-identical copy |
| Schedule | identical to run 1 (deterministic counterbalancing) |
| Command | `python3 scripts/run_metrics_overhead.py results/metrics-overhead-rc-62c2cea-r2 --measured-commit 62c2cea9314085f6f7669ebbb7def2be1fa1cb5c`, host checks enforced |
| Collection | 2026-11-15 18:24:38–18:29:52 UTC, 314.4 s, 74 observations, no extension |

## Results

Budget, approved before M6.5 and unchanged: PASS if the paired median ≤ 3%
and the 95% interval's upper bound ≤ 6%. REGRESSION if the lower bound > 3%
and the median exceeds the A/A bound. Otherwise INCONCLUSIVE.

| Scenario | Run 2 (evaluated) | A/A bound | Verdict | Run 1, for reference |
|---|---|---|---|---|
| `batch_1024_connected` | +1.07% [+0.78%, +1.59%] | ±0.82% | PASS | +1.24% [+0.27%, +3.29%] PASS |
| `batch_1024_cut_link` | +1.24% [+0.63%, +2.24%] | ±0.50% | PASS | +1.88% [+0.96%, +2.85%] PASS |
| `concurrent8_single_connected` | −0.22% [−1.10%, +1.64%] | ±2.35% | PASS | +0.43% [−1.29%, +2.06%] PASS |
| `feeder_events_1024` | +0.69% [−0.45%, +1.97%] | ±2.13% | PASS | +0.78% [−0.64%, +2.01%] PASS |
| `import_100000_chain` | −1.84% [−4.70%, +1.18%] | ±3.70% | PASS | +0.34% [−4.51%, +5.38%] PASS |
| `single_connected` | −11.08% [−12.13%, −8.06%] | ±1.80% | PASS | −11.01% [−12.44%, −7.19%] PASS |

**Outcome: 6 PASS of 6.** Under the plan, the M6.5 conclusion holds for the
release candidate. That means `/metrics` on/off overhead within the approved
budget, built with the shipped feature set.

**Checks, all passed:**
- **Observations:** 74, no failure or timeout, every stream hash matches.
- **Identity:** unchanged after the build and at the end.
- **Host:** all 25 host checks valid, with AC power, no thermal warning and
  no competing build.
- **Analysis:** `analyze.py --check` regenerates the outputs identically.
- **Agent activity:** none during the run. The session transcript shows a
  single agent tool call in the window, the launch command at 18:24:37.

## Deviations

- **Agent activity:** none.
- **Host condition, recorded and not a protocol deviation:** the 1-minute
  load average had a median of 2.99 (range 2.1–3.9), against 1.63 in M6.5.
  - It came from interactive applications running on the host.
  - It is within the protocol's host checks, which do not bound load
    average.

## Limits

- **Scope:** in-process router probe, no sockets, no tracing subscriber.
  Disabled log callsites take the same path in every arm. One host (Apple
  M3, macOS), Rust 1.100.0. Not a measurement of network, log-sink or
  production-host overhead.
- **`single_connected` is faster with metrics on in M6.5 (−12.9%) and in both
  RC runs (−11.0%, −11.1%).**
  - **Cause not established.** No code path is known to explain a speedup
    from enabling metrics.
  - **A hypothesis, not evidence:** the M6.5 README suggests start-up
    effects, because this scenario runs first in each process. No causal
    test of it exists.
  - **The recurrence is not proof:** that the result recurs does not by
    itself show that it is an artifact.
  - **No speedup claim:** the verdict only bounds slowdowns. No claim of
    speedup is made, and no threshold is changed retroactively.
