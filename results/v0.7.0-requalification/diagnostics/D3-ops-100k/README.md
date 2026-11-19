# D3 — B4 `ops` sparse 100k INCONCLUSIVE: where the lifecycle batch overhead goes

Diagnostic ordered on 2026-11-19 (DIAGNOSTICS-PLAN.md, D3). It is not part
of the qualification. The a3-3 result, INCONCLUSIVE +23.76% [+18.05, +26.72]
against a 25% tolerance, stands. This measurement is separate from it.

**Setup.** A diagnostic build of the candidate (`d3-instrument.diff`) adds
phase counters to the server's batch path (`knotrel_server::d3`, not a
product API). A diagnostic copy of the frozen `http-lifecycle`
(`d3-probe.diff`) resets them before each arm's window and reads them after
it. Otherwise the run is the frozen `--scenario ops --nodes 100000 --requests
40`, seed 5000001, 24 pairs after 2 warmup, alternating arms, in one run on
the developer laptop. Outputs are in `raw/`; `summary.txt` comes from
`phases.py`.

## Phase timing (median per window, `summary.txt`)

| Phase | Lifecycle server | Plain server + untimed planner | Difference | Share of the difference |
|---|---|---|---|---|
| Window (total) | 4,549.6 µs | 3,835.2 µs | +714.4 µs | 100% |
| Outside the handler (router, body parse, probe loop) | 1,214.0 | 1,421.9 | −207.9 | −29% |
| Handler | 3,343.9 | 2,406.6 | +937.4 | 131% |
| Applying the operations (under the lock) | 2,625.0 | 1,508.3 | **+1,116.7** | **156%** |
| Dispatch (admission, blocking hop, lock, join) | 146.5 | 147.9 | −1.4 | 0% |
| Lock wait | 0.8 | 0.8 | 0 | 0% |
| Response serialization | 571.2 | 752.8 | −181.5 | −25% |

The window ratio in this run is 1.199 (1.043–1.329).

**Operations per window:** the lifecycle trace sends 9,464 operations in 37
requests. The planner's equivalent plain trace sends 13,057 in 37. The
lifecycle arm parses and serializes less, but applies its fewer operations
more slowly: +74% applying time, +1.12 ms per window.

## Reading

- **The apply phase exceeds the whole window difference** (+1,117 µs, 156%
  of +714 µs). The handler's other phases and the outside-handler phase are
  lower for the lifecycle arm and offset part of it. The two arms apply
  different operation sets (9,464 lifecycle operations against 13,057 plain
  ones), so this is a phase attribution, not a per-operation comparison.
  Admission, the blocking-pool hop and the lock add nothing measurable.
- **Context from a3-3, not measured here.** The B1 core comparison
  (`B1-ops-compact-bfs-sparse-100000-mutation`: +1.47% [+0.62, +3.96]) times
  its application-side reference with that reference's bookkeeping. B4's
  reference plans untimed. The two cells measure different things, by design
  of the frozen protocol. This diagnostic does not assess either design.
- `knotrel-core` is byte-identical between v0.6.0 and v0.7.0. The rise from
  v0.6.0's +19.45% to +23.76% is not explained by this diagnostic. The
  server path changes in v0.7.0 (shared read lock, `sonic-rs`) apply to both
  arms.

## Sampling profile (weak; recorded, not relied on). Departure from the plan

The plan asked for six profiler windows per arm, alternating, with each
code site classed as inherent or optimizable. What was run is one `sample`
over 25 s of 35 pairs, with no per-arm difference and no classification.
That plan item is not met.

`raw/sample-ops-100k.txt` comes from macOS `sample` at 1 ms over 25 s of 35
pairs (debug-info build). The windows are a small share of the run: setup and
checks dominate.
- **Main thread** (`window-profile.txt`): only 113 samples fell inside
  `run_window`, mostly request parsing (`simd_json`) and response
  serialization. The operations run on blocking-pool threads.
- **Inside window-only lifecycle operations** (`set_node_active`,
  `set_edge_enabled`, `remove_node`; `lifecycle-ops-profile.txt`): 65
  samples. The largest are `Graph::cut` and `memmove` (adjacency vector
  shifts), plus probe-model frames. That is too few samples for a code-site
  ranking.

## What this establishes (no verdict)

- **Actionable costs**, if any, are in the time spent applying lifecycle
  operations (`knotrel-core`), not in the server's admission, lock or
  dispatch. Making them cheaper would be a core change. This diagnostic does
  not change or reinterpret the B4 rule or its reference.
- **The instrumentation** adds the same counters to both arms. Its cost was
  not measured separately.
- **Provenance.** The build record reads `probes_dirty: true` (the diagnostic
  probe copy). That `knotrel-core` is unchanged since v0.6.0 is stated in the
  comparison report, not shown here.
- **A ranked code-site profile needs a window-only profiler.** For example, a
  core-only replay of the B4 trace under `sample`. That is not done here.
