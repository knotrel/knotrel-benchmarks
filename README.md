# Knotrel benchmarks

Reproducible workloads for measuring exact dynamic graph connectivity.

The initial harness measures `knotrel-core` directly using a seeded chain
split/rejoin workload. It validates every result and emits a JSON report with
operation latency distributions, configuration, build compiler and checkout
metadata. GraphScope, HTTP, production workload and memory-measurement adapters
are **not implemented yet**. This repository makes no comparative speedup claims.

## Local layout

Keep both repositories in the same parent directory, named `knotrel` and
`knotrel-benchmarks`. The workspace uses `../knotrel/crates/knotrel-core` as a path
dependency, so edits in your local core are measured immediately.

Both workspaces pin Rust **1.98.1**, edition **2024** and resolver **3**. Third-party
dependencies are locked in Cargo.lock. The path dependency is intentionally not
revision-pinned: record the exact core revision and diff with every result.

## Run

```sh
cargo run --release --locked -- --nodes 10000 --rounds 1000 --seed 42
```

Use `--help` for arguments. The defaults match the command above. Repeated flags
use the last value. Each round performs one cut, a disconnected query, one link,
and a connected query. The initial graph has `nodes` vertices and `nodes - 1`
edges. All deleted edges are bridges; this is a narrow baseline, not a general
graph workload. Use release builds for measurements.

The report labels debug builds, contains per-operation min/p50/p95/p99/max and
total nanoseconds, and identifies the trace as `chain-split-rejoin-v1`.
Checkout metadata describes sources present at run time; moving an already-built
binary or changing sources after compilation invalidates binary provenance.
For reproducible published runs, build and run from clean, recorded revisions.

## Development

```sh
cargo fmt --all -- --check
cargo clippy --workspace --all-targets --locked -- -D warnings
cargo test --workspace --locked
RUSTDOCFLAGS='-D warnings' cargo doc --workspace --no-deps --locked
```

All public items require English Rustdoc. Complex private code documents
invariants and costs. See [methodology](docs/methodology.md) before comparing
engines. CI checks out the sibling core repository; its Rust foundation must
exist in the selected core revision first. Manual CI runs accept `core_ref`;
automatic CI checks compatibility with core `main` and logs the resolved revision.
