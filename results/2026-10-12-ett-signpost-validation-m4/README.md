# ETT scan-root signpost validation on Apple M4 — 2026-10-12

This diagnostic verifies whether a safe, isolated `apple-log` signpost wrapper
can delimit the ETT replay loop in Xcode Instruments. It changes neither
production source nor the scan-root candidate.

The [protocol](protocol.md) fixes two marker-validation traces before
collection. [build.py](build.py) reconstructs both historical source variants
in isolated workspaces, adds `apple-log` only there, and runs the required
formatting, Clippy, tests/doctests, Rustdoc, and release-build checks.
[collect.py](collect.py) verifies marker visibility and ordering in exported
`OSSignpostIntervals` data.

## Result

Both fixed CPU Counters recordings completed successfully with temporary sleep
inhibition active. Each target process emitted an ordered `warmup-replay`
interval followed by a `measurement-replay` interval on its main thread:

| Variant | Warmup interval | Measurement interval | Benchmark wall interval |
|---|---:|---:|---:|
| Before | 7.224 ms | 7.586 ms | 7.584 ms |
| After | 7.570 ms | 5.502 ms | 5.500 ms |

The marker duration agrees with the runner's measured interval to the expected
small boundary overhead. This validates replay scoping, not a performance
comparison: there is only one recording per variant in this validation.

The first collector result reported a false failure because it did not resolve
Instruments XML references and searched for a `name` field rather than the
exported `signpost-name` field. The immutable XML exports contain the expected
markers; [analysis.json](analysis.json) records the corrected post-collection
validation. No trace was repeated.

The two raw trace bundles are external to Git at:

`$SESSION_STATE/files/ett-signpost-validation-m4-traces`

Their tree hashes are retained in [analysis.json](analysis.json). The successful
result authorizes the separate 72-trace
[marker-scoped CPU Counters campaign](../2026-10-12-ett-hardware-profile-m4-signposted/README.md).
