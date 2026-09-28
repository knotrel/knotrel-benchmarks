# Verification

Verified all recorded source and artifact SHA-256 hashes; all processes exit 0
without timeout and have measured peak RSS. Trace fingerprints match across
backends/trials/regimes for each configuration. Operation counts, query ratios
and extra-repeat counts match requests. Summary CSV matches raw recomputation.

Core/server: 20 tests and one doctest pass. Benchmark workspace: 14 tests pass.
Python helper/protocol suite: 10 tests pass. Formatting, Clippy and Rustdoc with
warnings denied pass in both workspaces. Independent review found no remaining
correctness issue after fixing process-group timeout termination and documenting
free-list growth. No commits or pushes. README/summary/verification were written
after collection and are outside the original artifact hash set.
