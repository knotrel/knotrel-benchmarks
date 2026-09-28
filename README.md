# Knotrel benchmarks

Reproducible workloads for measuring exact dynamic graph connectivity.

The harness compares [`knotrel-core`](https://github.com/knotrel/knotrel), the compact production core, an experimental BFS, petgraph DFS and outils HDT using four deterministic synthetic
workloads: a path, a cycle, joining/splitting components, and a degree-skewed hub.
It validates every result and supports trace export, warmup and separate reports
for repeated fresh-graph runs. GraphScope, HTTP, real-world datasets and memory
measurement are **not measured**. The prepared GraphScope probe remains unverified.
See [competitor selection and adoption](docs/research/2026-09-26-competitive-landscape.md)
and the [measured embedded comparison](results/2026-09-26-competitors/README.md).
Petgraph is the primary external baseline; outils is an algorithmic control.

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

Select a workload and save a reusable trace:

```sh
cargo run --release --locked -- --workload cycle-alternatives-v1 --nodes 4096 --rounds 200 --seed 42 --warmup 1 --repetitions 3 --trace-out cycle.trace.json
```

`--help` lists all families and flags. Defaults preserve the original chain
sequence, with one warmup and one measured replay. Each repetition starts with
a fresh graph. Trace output refuses to overwrite files. JSON report schema 2
stores latency summaries under `repetitions[i].measurements`, with separate
cut/link/connected summaries; it also records topology and trace fingerprint.

See [methodology](docs/methodology.md) for topology, ratios, timing boundaries,
trace interchange and limitations. The [local release baseline](results/2026-09-26-macos/README.md)
contains raw results and reproducibility metadata. Reproduce the complete matrix:

```sh
python3 scripts/run_baseline.py results/NEW_RUN_DIRECTORY
```

## Development

```sh
cargo fmt --all -- --check
cargo clippy --workspace --all-targets --locked -- -D warnings
cargo test --workspace --locked
RUSTDOCFLAGS='-D warnings' cargo doc --workspace --no-deps --locked
```

All public items require English Rustdoc. Complex private code documents
invariants and costs. See [methodology](docs/methodology.md) before comparing
engines. CI checks out the sibling [core repository](https://github.com/knotrel/knotrel); its Rust foundation must
exist in the selected core revision first. Manual CI runs accept `core_ref`;
automatic CI checks compatibility with core `main` and logs the resolved revision.

## Comparing backends

```sh
cargo run --release --locked -- --engine all --nodes 4096 --rounds 100 --query-repeats 1 --repetitions 3
```

Multiple engines produce schema 3 containing one schema-2 report per backend.
Setup, original true/false queries and immediate repeated queries are reported
separately. Repeats augment the workload; no hardware-cache flushing is implied.
For the full recorded protocol with independent process trials and rotated order:

```sh
python3 scripts/run_baseline.py results/NEW_COMPARISON --nodes 128 1024 4096 --rounds 100 --process-trials 4 --repetitions 3 --cache-regimes both --engines all --query-repeats 1
python3 scripts/summarize_comparison.py results/NEW_COMPARISON
```

`--engine compact-bfs` measures the default production `Graph`; `reference-bfs`
continues to measure the preserved ordered `ReferenceGraph`. The `all` selector
now includes the compact backend; see below for the current full set.
See the [compact-core results](results/2026-09-27-compact-core/README.md).

## Dynamic forest and scale workloads

`--engine ett-scan` selects the experimental maintained forest. `all` now contains
eight backends (use eight process trials to balance their positions). For sustained
churn and process memory measurements:

```sh
python3 scripts/run_scale.py results/NEW_SCALE_RUN --nodes 10000 100000 --query-percent 10 50 90 99 --rounds 20 --trials 2
python3 scripts/summarize_scale.py results/NEW_SCALE_RUN
```

One round is 100 operations for the new sustained families. RSS covers the whole
process, including the harness. See [scale results](results/2026-09-27-forest-scale/README.md).

The experimental forest now uses candidate-subtree pruning. Compare it with the
frozen prototype via `--engines ett-scan-v1 ett-scan` in the scale collector.
See [pruning measurements](results/2026-09-27-forest-pruned/README.md); `all` now
contains nine backends, including experimental Knotrel HDT and its frozen v2 control. Counter definitions differ by version as documented.


## Experimental Knotrel HDT

`--engine hdt` selects `knotrel-core/hdt-sparse-levels-v3`, with separate `hdt_stats`
promotion/search counters. HDT maintains multiple forests and uses more memory;
its update bound is amortized. Neither the default core nor the existing ETT
backend changed. Dense stress families `dense-bridge-churn-v1` and
`redundant-bridge-churn-v1` keep two cliques fixed and toggle one or two bridges.
They use 100 operations per round and support `--query-percent`; setup has
quadratic edge count, so choose bounded node sizes.

```sh
python3 scripts/run_scale.py results/NEW_HDT_RUN --nodes 128 512 \
  --workloads dense-bridge-churn-v1 redundant-bridge-churn-v1 \
  --query-percent 50 99 --rounds 20 --trials 2 \
  --engines compact-bfs petgraph-dfs ett-scan hdt
python3 scripts/summarize_scale.py results/NEW_HDT_RUN
```

A repeated-query control can use `--query-repeats 1` in a separate collection.
Use the sparse sustained families too; these dense cases deliberately target
repeated scans and cannot establish a general performance or adoption claim.

See the [HDT comparison report](results/2026-09-28-hdt-v2-dense/README.md) for
measured dense wins, sparse regressions, setup, update tails and memory costs.

### HDT storage diagnostics

`cargo run --release --locked --bin hdt-profile -- --engine hdt-v2 --nodes 512 --rounds 10 --workload dense-bridge-churn-v1 --query-percent 50` replays the same deterministic trace and independent query oracle as the normal runner. Use `--engine hdt` for the current sparse v3 implementation. The default binary remains `knotrel-benchmarks`.

The JSON contains structural storage snapshots after registration, initial edges and replay, registration/loading stage durations, cumulative work counters and operation latency groups (links, queries, tree cuts with or without promotions, and non-tree cuts). Snapshots, counter reads, classification and correctness checks are outside operation timers. Counter reads and intervening snapshot allocations perturb caches: these diagnostic timings must not be compared with normal benchmark timings. Vector capacity bytes and live ordered-container payload bytes exclude allocator and B-tree overhead; they are not RSS or total heap usage.

See the [v3 memory/time comparison](results/2026-09-28-hdt-v3-sparse/README.md):
sparse upper levels reduce storage substantially but add measured cyclic repair
cost. Frozen `hdt-v2` remains a same-build comparison control. To reproduce the
diagnostic collection against a normal run's saved sources:

```sh
python3 scripts/run_hdt_profile.py results/NEW_PROFILE \
  --source-manifest results/NEW_NORMAL_RUN/manifest.json
```

Result publication keeps compact measurements and provenance in Git; bulky trace
exports remain local. See the [artifact policy](results/README.md) and trace hash
inventory before attempting a full historical artifact audit from a fresh clone.
