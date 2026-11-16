# v0.5.0 run 4 — candidate dcd8ccc, lifecycle scope compact-bfs (amendment 4)

**Delivered scope (owner decision B1):** node and edge lifecycle on `compact-bfs`
only; `ett`/`hdt` lifecycle rejected explicitly (core constructors return
`LifecycleError::UnsupportedEngine`; `ServerConfig::with_topology_lifecycle(true)`
and `KNOTREL_TOPOLOGY_LIFECYCLE=true` fail for those engines before a router is
built or a port bound); non-lifecycle `ett`/`hdt` and every pre-v0.5.0 API
unchanged.

**Candidate:** knotrel `dcd8ccca10ef5766e3c9252832594186bf93bbc3`, clean;
validation 14/14 (`evidence/v0.5.0-dev/validation-dcd8ccc/`, python-tests after
a cargo cache fix, see its `VALIDATION-NOTE.md`). Reviews: contract/compatibility
and code, no blocker or major; minors fixed. Amendment 4 verified independently
before measurement (PASS WITH CORRECTIONS, corrections applied and re-verified).

## Results

| Gate | Result (dcd8ccc) | Evidence |
|---|---|---|
| A vs v0.4.0 | 6 PASS, 1 INCONCLUSIVE_DISCLOSED, **2 UNRESOLVED** (batch 1 request p99; batch 64 RSS upper bound 25.14% vs 20%), no REGRESSION | `A-20261116T113709Z-dcd8ccc/RESULT.md` |
| B1 core ops | 20 PASS | `BC-final-dcd8ccc/analysis.md` |
| B2 opt-in | 9 PASS | |
| B3 degree | 8 PASS | |
| B4 HTTP/feeder | 19 PASS, **2 REGRESSION**, **3 INCONCLUSIVE** | |
| B5 memory | 2 PASS (2.45×, 2.44× plain heap) | |
| C1 slots / C2 counts | 30 / 60 PASS | |
| C3 heap growth | 12 PASS, **3 FAIL** (fresh-ID churn, 100k: sparse, ring, hub) | |
| C4 RSS (disclosure) | 7 PASS, 8 EXCEEDS_BUDGET | |

B4 non-PASS cells:
- REGRESSION: `import` sparse 100k +109.9% [101.9, 115.9] (t = 100%); `import-high`
  (60% inactive, 30% disabled) sparse 10k +444.8% [427.3, 464.6].
- INCONCLUSIVE: `import` sparse 10k +100.8% [96.1, 107.0]; `metrics-ops` +6.5%
  [5.3, 8.3] (t = 6%); `metrics-legacy` on `ett` (lifecycle-disabled servers)
  +4.0% [1.0, 6.4] (t = 6%; PASS in run 3).
- `ops` sparse 10k and 100k: PASS (+19.8% [18.1, 20.4], +19.5% [16.5, 22.7]);
  they were INCONCLUSIVE in run 3 (non-quiet host).

C3 FAILs: compaction sawtooth under fresh-ID churn; engine slots stayed within
2V + 1024 (C1 PASS at every checkpoint).

## Memory peaks (D5, diagnostic, compact-bfs 100k; identical to D4 on a1d9577)

| Run | Steady max (net live) | Peak (net live) |
|---|---|---|
| fresh-ID churn (compaction at cycle 20) | 37.3 MiB | 49.2 MiB (+11.9) |
| same-ID churn | 24.1 MiB | 27.0 MiB |
| toggle churn | 23.0 MiB | 23.0 MiB |
| core import 20/10 → 60/30 | final 25.5 / 23.6 MiB (incl. inputs) | 28.2 / 24.8 MiB |
| HTTP import create 20/10, 60/30 | final 24.3 / 22.4 MiB | 111.2 / 128.6 MiB |
| HTTP import replace 20/10 (old graph live) | final 24.3 MiB | 130.3 MiB |

RSS at cycle 30: 66-103 MiB (allocator retention; no hard bound).

## Applicability and history

Earlier candidates' results (runs 1-3, A for `6494253` and `a1d9577`, D1-D4)
are unchanged. The `ett`/`hdt` lifecycle results of earlier candidates remain
recorded and are not passes; they are outside the delivered scope. Run 3's
non-quiet host is disclosed in `RUN3-CONCURRENT-ACTIVITY.md`; run 4 was
collected on a quiet host.

## Budget

Logged measured time: 187.0 min (151.6 before, pilot 6 1.4, A 26.8, B/C 7.2,
D5 < 0.1) plus at most 15 min unlogged diagnostics: at most 3 h 22 min of the
six hours.
