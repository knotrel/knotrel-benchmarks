# Local verification

Executed on 2026-09-26 with the pinned Rust 1.98.1 aarch64-apple-darwin toolchain.
Both repositories were clean before this milestone. HEADs remain unchanged:

- Core/server: [`87ca572`](https://github.com/knotrel/knotrel/tree/87ca572223b6657836db14aa34338c7855d56859).
- Benchmarks: [`9a20223`](https://github.com/knotrel/knotrel-benchmarks/tree/9a20223c54e3f0383b0300a1cdd4b7d40cc6bb3e).

## Before changes

In each workspace, all four required commands passed:

```sh
cargo fmt --all -- --check
cargo clippy --workspace --all-targets --locked -- -D warnings
cargo test --workspace --locked
RUSTDOCFLAGS='-D warnings' cargo doc --workspace --no-deps --locked
```

Core/server: 13 tests and one doctest. Benchmarks: six tests.
The release chain smoke command with `--nodes 128 --rounds 10 --seed 42` passed.

## After changes

The same four commands passed in both workspaces. Core/server: 13 tests and one
doctest. Benchmarks: nine tests, including a matrix oracle covering 36 family /
size / seed combinations and stable-export/overwrite checks. The first new CLI
oracle test failed on the missing `--workload` flag before implementation.

`cargo build --workspace --release --locked` passed in the main repository.
The benchmark release build, all 12 recorded configurations (36 measured
repetitions), and the original release smoke command passed. All runtime
answers and mutations matched their expected outcomes.

A separate integrity audit verified all 27 artifact SHA-256 hashes and all 23
current build-input SHA-256 hashes against the manifest. It independently
recomputed all 12 FNV trace fingerprints and initial maximum degrees, and checked
all 36 repetition operation counts against the exported traces. `git diff
--check` passed in both repositories. Cargo.lock files, licenses, core and
server code remain unchanged. No commits or pushes were made.

The benchmark collection first stopped because sandboxed hardware discovery was
denied. After optional metadata discovery was made non-fatal, the complete matrix
succeeded. A separately authorized read supplied the hardware values in README.

No new real-socket HTTP smoke session was run in this milestone; the existing
six HTTP integration tests passed. The optimized engine, GraphScope adapter,
HTTP benchmark and memory profiling were not implemented or measured.

## Independent review follow-up

Review found that a fixed executable path could select a stale binary when Cargo
uses a custom target directory. The script now reads Cargo's JSON compiler-artifact
output and runs exactly the reported executable. A second complete 12-configuration
matrix succeeded with `CARGO_TARGET_DIR=/private/tmp/knotrel-review-target-20260926`;
all recorded commands used that custom executable. Those auxiliary validation
measurements live in `/private/tmp/knotrel-review-results-20260926` and are not
included in the baseline table. No Rust build inputs changed after the baseline.
The review found no other important issues in generation, oracle, timing or ADR.
