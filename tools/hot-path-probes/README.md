# hot-path-probes

Measurement tools for the knotrel hot-path audit campaign
([`results/hot-path-audit-20261114/`](https://github.com/knotrel/knotrel-benchmarks/blob/v0.4.0/results/hot-path-audit-20261114/README.md)),
driven by [`scripts/run_hot_path_audit.py`](../../scripts/run_hot_path_audit.py).

| Binary | Purpose |
| --- | --- |
| `router-probe` | Drives the complete `knotrel-server` router in process (`tower::ServiceExt::oneshot`, no sockets) through six scenarios: one connectivity query, eight concurrent clients, a batch of 1,024 queries, a batch of 1,024 alternating cuts/links, an import of 100,000 nodes and 99,999 edges, and a feeder batch of 1,024 events. Modes: `timing` (default build, mimalloc), `count` (`--features count-alloc`), `verify` (normalized-response digests). |
| `job-tracking` | Mechanism microbenchmarks replicating server patterns in isolation: the outstanding-job counter (`watch` versus atomic plus `Notify`), metric-family lookup versus a cached handle, a millisecond clock read, and body copying versus conversion. They do not call Knotrel code. |

## Allocators

- The default build installs **mimalloc**, like `knotrel-server`. Use it for
  `timing` and for `job-tracking`.
- `--features count-alloc` installs the **system allocator wrapped by
  `stats_alloc`**, which counts allocations, reallocations and bytes. Use it
  only for `count`. Its timings are not production timings and are never
  reported.

The crate contains no `unsafe` code; the counting wrapper comes from
`stats_alloc` (MIT).

## Workspace and license boundary

This crate is its own Cargo workspace with its own `Cargo.lock`. It is not a
member of the `knotrel-benchmarks` workspace, for two reasons:

- `router-probe` links `knotrel-server`, which is licensed under Elastic-2.0,
  and its HTTP stack. Keeping it out of the Apache-2.0 workspace leaves the
  workspace `Cargo.lock` and its cargo-deny license policy unchanged.
- The probe source is Apache-2.0. Binaries built from it include
  Elastic-2.0 code and are intended for local measurement only.

The probe constructs JSON request bodies for public endpoints but contains no
HTTP client, and it uses only the public `knotrel-server` API
(`router_with_lifecycle`, `ServerConfig`, `Lifecycle`).

## Building

The manifest's default `knotrel-server` path is the sibling checkout
(`../../../knotrel`). The collector copies this crate and rewrites that path
to build the baseline and candidate trees separately.

```sh
cargo build --release --locked                          # timing + job-tracking
cargo build --release --locked --features count-alloc   # count
```
