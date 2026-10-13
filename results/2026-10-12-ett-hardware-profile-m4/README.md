# ETT scan-root hardware-profile feasibility on Apple M4 — 2026-10-12

This directory is a new diagnostic campaign. It does not alter the historical
results in `2026-10-10-*`, production sources, candidate disposition, or any
engine ranking.

The predeclared [protocol](protocol.md) defines an isolated reconstruction of
the exact scan-root candidate and six non-repeating CPU Counters trace attempts:
path at one million vertices in fresh and warmed regimes, plus the dense
positive control. [build.py](build.py) records source and binary provenance;
[collect.py](collect.py) records Xcode 27 trace metadata, every failure, and
the complete-process trace table of contents.

## Result

All six `xctrace` commands exited successfully. Every benchmark output has the
expected trace fingerprint, and temporary `caffeinate -is` assertions were
visible while each trace was recorded. The saved power-log interval contains no
actual `Sleep`, `Wake`, or `DarkWake` event.

The profiler recorded **zero** `OSSignpostIntervals` in every trace. It did
record process/thread counter rows and core labels, but each target process has
only one directly identified counter interval (89–458 microseconds) while the
complete process also includes 4.5 ms–1.37 s of setup and, for warmed cases, a
full warmup replay. The internal replay durations were 5.5–8.9 ms for path and
18.0–32.0 ms for dense. The 10 ms CPU Counters process bucket and missing
signpost interval therefore do not provide a replay-scoped sample.

Consequently:

- no cache, TLB, page-fault, allocation, instruction, cycle, stall, scheduler,
  core, frequency, or energy conclusion is made from these traces;
- core labels (`CPU 6`, `CPU 8`, and `CPU 9`, all P cores) are observations of
  whole-process counter samples, not demonstrated replay placement or
  migration;
- one profile sample per variant is not a timing distribution. Its path and
  dense wall times are retained only as raw diagnostic observations, not as
  evidence that the path variability reproduced or that the dense control
  passed;
- the path variability remains **inconclusive** on this host. The scan-root
  candidate remains isolated.

[analysis.json](analysis.json) contains the machine-readable row counts,
benchmark replay boundaries, power result, counter-scope flag, and deterministic
hashes for all raw artifacts. [verification.json](verification.json) records
formatting, Clippy, tests/doctests, Rustdoc, and release builds for both isolated
variants. The first isolated check failed only because the locked `outils`
dependency was absent from the local cache; [build-attempts.json](build-attempts.json)
retains that failure and its non-manifest-changing recovery.

## Raw trace artifacts

The six `.trace` bundles and large counter/activity XML exports totalled about
806 MiB and are intentionally outside the Git worktree at:

`$SESSION_STATE/files/ett-hardware-profile-m4-traces`

Their deterministic tree/file hashes are in [analysis.json](analysis.json).
The repository retains the trace table-of-contents files and empty signpost
exports, so the scope limitation remains independently inspectable. Set
`KNOTREL_TRACE_ARTIFACT_DIR` to the stored location when rerunning
`analyze.py`.
