# Verification

All source and artifact hashes verified, including archived source for the
Rustdoc-only clarification noted below. Every process exited successfully with
measured RSS and no timeout. Exact requested operation/query/repeat counts and
shared trace fingerprints were checked. Summary CSV matches raw recomputation.
Paired v1/v2 runs have identical tree-cut, candidate-edge and replacement counts.

Core/server: 23 tests and one doctest pass. Benchmarks: 16 Rust tests pass.
Python: 10 helper/protocol tests pass. Both workspaces pass formatting, Clippy
and Rustdoc with warnings denied. Independent review found no correctness defect
and verified the frozen baseline; its counter-documentation clarification is
applied. No commits/pushes. Later summary/docs are outside original artifact hashes.
