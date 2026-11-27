# v1.2.0: candidate status after the BFS restore (knotrel#182)

Recorded 2026-11-27, after the maintainer chose to restore the v1.1.0 BFS
(knotrel#205, merged as 25fadec). The BFS experiment line is closed.

## The measured candidate keeps its verdicts

The attempt-1 results ([`REPORT.md`](REPORT.md), `attempt1/`) belong to candidate **9faf168**
(bidirectional BFS, #196) and stay as they are. Attempt 1 stays valid, and 9faf168 stays not
qualified.

| Item | Native verdict |
|---|---|
| K1: chain-split-rejoin 10k, 100k; cycle-alternatives 10k, 100k; components-join-split 10k, 100k; sustained-churn-path 100k | `REGRESSION` |
| V1: sparse traversal compact-bfs; sparse traversal compact-workspace; sustained churn compact-bfs | `REGRESSION` |
| K1 sustained-churn-blocks 10k and sustained-churn-path 10k | `TIMER_LIMITED` |
| V1 `http_lifecycle_compact_bfs_small` | `INCONCLUSIVE_DISCLOSED` |
| V1 `http_standalone_batch_b1_compact_bfs` and `b256` | `UNRESOLVED` |
| B4 deciding cells (23, including `ops-atomic` hub 10k) | `PASS` |
| V2, K2 | `PASS` |
| Q1, Q2, Q4, Q5 | `PASS` |
| **Q3** | **`FAIL`**: C=16 at 48.5 % (threshold 50 %), C=64 at 33.5 % (threshold 25 %) |

Follow-up records:
- the [diagnosis](diagnosis/REPORT.md);
- the [#203 estimate](../v1.2.0-bfs-layer-fix/REPORT.md), REJECT;
- the [#204 estimate](../v1.2.0-adaptive-bfs/REPORT.md), REJECT.

## The resulting candidate: `main` at 25fadec, compared with v1.1.0

`git diff v1.1.0 25fadec` touches 8 files:

| Area | Change | Product effect |
|---|---|---|
| `crates/knotrel-core/src/lib.rs` | a doctest example in `Graph::connected`'s documentation | none: the executable code equals v1.1.0 |
| `crates/knotrel-core/tests/connectivity.rs` | two differential tests (all pairs; random histories) | none (tests) |
| `docs/design/` | the #181 impact-estimate protocol, the #151 compact-index design (REJECTED), the hub 10k reference design | none (documentation) |
| `docs/integrations/feeder-under-load.md` | the v1.2.0 B1/B2 decision record | none (documentation) |
| `docs/releases/` | the release procedure (per-release policy, #186) and the v1.2.0 qualification plan | none (documentation) |

Unchanged since v1.1.0:
- `knotrel-server`, the integrations (the PostgreSQL feeder included);
- `Cargo.lock`, the toolchain and server defaults.

**No product change remains to release.** Nothing in the diff justifies a minor release on
its own. As the maintainer decided, **v1.2.0 stays open until the B2 decision on knotrel#87**.
The next #182 attempt will be scheduled once the candidate to qualify is defined.

## Feeder reference for the restored candidate (historical, not a verdict)

The restored candidate runs v1.1.0's query path. Its Q3 position is therefore given by the
historical measurements of that path, not by a new verdict:

| Source | L2 G100k C=16 share | C=64 share |
|---|---|---|
| #181 impact estimate, base arm (cd57816 = v1.1.0 core and server code), 3 observations | **15.0 %** | 9.6 % |
| CF5 S3 (v1.1.0 qualification), `compact-bfs` | 16.6 % | 9.1 % |

**This is the reference for the B2 design.** The 48.5 % of attempt 1 belongs to 9faf168
only.
