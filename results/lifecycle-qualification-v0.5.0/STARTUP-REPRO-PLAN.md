# Startup-test reproduction plan (frozen before execution)

Target: the single observed failure of
`test_external_server_engine_mismatch_rejection`
(`crates/knotrel-server/tests/measure_e2e_driver.rs`, panic "External server
died prematurely", seen once during a `cargo test --release --workspace` run on
`7f19b11`; server stderr was discarded).

Instrumentation (diagnostic patch `driver-diag.patch`, test code only): the
external server's stderr goes to a file in a per-guard temporary directory,
removed after the child is killed and reaped; a premature exit or a missed
readiness deadline panics with the exit status and that stderr (or the I/O
error that prevented reading it). No retry is added. A new test,
`test_external_server_startup_failure_reports_server_stderr`, checks that a
failing server's own error message is reported.

Runs: candidates `6494253` (fresh clone, patch applied) and `a1d9577`
(worktree, patch applied). The test-file source is identical in both and
`knotrel-server` is unchanged between them. Each candidate: release build of
the test targets first, then **20** executions of
`cargo test --release -p knotrel-server --test measure_e2e_driver` with the
default test-thread count, alternating candidates (6494253, a1d9577, ...).
Every execution's full output and exit status are kept in
`startup-repro/<candidate>/run-NN.{log,exit}`. No measurement or other campaign
runs at the same time. Stop after 40 executions whatever the outcome.

Interpretation fixed in advance: a failure whose captured server stderr shows a
bind error (address in use) confirms the port race in `free_address()`; any
other captured cause is reported as found; no failure in 40 executions means the
cause remains **not established** (no "pre-existing flaky" label).

## Addendum (frozen after the 40 executions, before the post-fix runs)

Outcome of the 40 executions: `a1d9577` run 18 failed in
`test_external_server_engine_mismatch_rejection` with captured server stderr
`Error: Os { code: 48, kind: AddrInUse, message: "Address already in use" }`;
`6494253` run 1 failed in a different test,
`test_regression_early_exit_with_diagnostics` (elapsed 1.59 s against its
timing assertion, first execution, 24.2 s total). Race confirmed. Fix: the
guard starts the server on `127.0.0.1:0` and reads the bound address from the
server's JSON startup line; new test `test_external_server_uses_its_own_bound_address`.
Post-fix check: exactly **20** further executions on the worktree with the
fix (`startup-repro/a1d9577-fixed/`), then stop. Absence of failures there
shows no recurrence in 20 runs, not absence of the race in general.
