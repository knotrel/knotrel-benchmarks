# Knotrel v0.5.0 vs v0.4.0 — release performance comparison

Per-release comparison required by the knotrel release procedure
("Per-release performance diff and paired tags"). It is assembled from the
v0.5.0 qualification evidence; no new campaign was run for it. The knotrel
v0.5.0 release notes remain the authoritative statement.

**Outcome:** v0.5.0 is **not demonstrated to be faster** than v0.4.0. With
lifecycle off: 6 PASS, 1 INCONCLUSIVE_DISCLOSED, **2 UNRESOLVED**, no
REGRESSION. The two UNRESOLVED results are accepted by maintainer waivers for
v0.5.0 only ([decision](MAINTAINER-DECISION-v0.5.0.md)); they are not passes.

## Identities

| | Previous release (B) | Candidate (C) |
|---|---|---|
| Version | v0.4.0 (tag `v0.4.0`) | v0.5.0 candidate (measured), release commit below |
| knotrel commit | `556683c8beb1ffe90fbf645bcf7955880690df2c` | `dcd8ccca10ef5766e3c9252832594186bf93bbc3` |
| `knotrel-server` binary sha256 | `0b1d71dd9b2fc9f0f972adb6ab4bf5be5a2014b53094076ab2d27b568b6c1a08` | `71d8acaf2a88e6a128ead8401c162d36ffc99d5fedb1da8373c053fb37deb4b7` |
| Core harness (`knotrel-benchmarks` at `df635a1e`) sha256 | `5c186a14920f866c3375cf5582efd39060826f796301ea516f134845765cb2bb` | `28b7a8d2b9d9665aa391cfa442299649652c78043b4514a458c913c4c22bee6f` |

- **Shared HTTP driver** `measure_e2e` (built from the candidate source):
  `88f0afb1f1d602ecfbb6fb5d2c3fad0f225a42dc0ec35c5c3fa6ba7f8160a2d4`.
- **Harness:** knotrel-benchmarks `df635a1e872fd9e2d556b166ac23f342ee45d675` (the v0.4.0 core
  harness) with derived lockfiles that change only the `knotrel-core` version.
- **Collector and analysis:** `run_p0_aa.py` and `prepare_bc_qualification.py`
  byte-identical to the v0.4.0 collector; `analyze_bc_qualification.py` with
  only the later path-containment fix (outputs unchanged; analysis script
  sha256 `3fcebe951c95841f2b2c54f2259b71d6a8c98878133b557f70dace0cc2577f21`). Decision rules: v0.4.0.
- **Lifecycle-cost cells** (not a release-to-release comparison): run with
  knotrel-benchmarks `c0dbe65760009df871492752121b2b4ce8fa17da`, probes built
  from `f1d099cc5b66be609a9624c2cab3169104223d2b`, against knotrel
  `dcd8ccca10ef5766e3c9252832594186bf93bbc3`.
- **Host and toolchain:** one Apple M3, macOS 26.5.2, AC power, quiet host;
  rustc 1.100.0, release profile, `--locked`.
- **Runtime configuration:** servers start with a cleared environment except
  `KNOTREL_ADDR`, `KNOTREL_MODE` (standalone) and `KNOTREL_ENGINE`
  (`compact-bfs`), so lifecycle and `/metrics` are off and every other setting
  is at its default; server stdout goes to `/dev/null` and stderr is captured
  by the driver.
- **Campaign:** main phase 2026-11-16T11:49:20Z–12:02:46Z (108
  pairs), extension 12:02:46Z–12:16:06Z (48 pairs, 4 cells);
  interleaved B/C pairs in fresh processes, shuffled order.
- **Release commit:** the knotrel commit tagged `v0.5.0` must contain the same
  executed code as `dcd8ccc`; that is verified on the
  release commit by comparing the `__TEXT,__text` sections of the release
  `knotrel-server` and `examples/lifecycle` builds, and recorded in the release
  notes.

## How to read the tables

- **Paired change** is `exp(median(ln(C/B))) − 1` over the pairs; positive means
  v0.5.0 is slower or uses more memory. It can differ in sign from the ratio of
  the two medians shown, which are computed independently.
- **Interval:** paired log ratios ln(C/B); one-based order statistics n=12 r(3),r(10); n=24 r(7),r(18). It is not a significance test.
- **Tolerances:** primary 10%, tail latency
  25%, RSS 20%.
- **PASS** means the interval's upper bound is within the tolerance; it is a
  regression decision, not proof of a speedup or of no change. Under the v0.4.0
  rules a cell is PASS only if every gated metric passes; a passing primary
  with an inconclusive gated metric is **UNRESOLVED**. The startup cell is
  INCONCLUSIVE_DISCLOSED under the existing disclosure policy.

## Primary metric per cell

| Cell | Pairs | Primary metric: v0.4.0 → v0.5.0 candidate (median) | Paired change [interval] | Tolerance | Primary | Cell outcome |
|---|---|---|---|---|---|---|
| Core sparse traversal, 10k, `compact-bfs` | 12 | 5.470 ms → 4.642 ms (`workload_wall_ns`) | −7.23% [−33.47%, +2.83%] | 10% | PASS | PASS |
| Core sparse traversal, 10k, `compact-workspace` | 12 | 5.212 ms → 5.097 ms (`workload_wall_ns`) | −1.94% [−9.87%, +6.00%] | 10% | PASS | PASS |
| Core sustained churn, 10k, `compact-bfs` | 12 | 683.6 µs → 679.5 µs (`workload_wall_ns`) | −1.02% [−3.67%, +0.64%] | 10% | PASS | PASS |
| Core sustained churn, 10k, `compact-workspace` | 12 | 476.0 µs → 477.5 µs (`workload_wall_ns`) | +0.19% [−1.38%, +2.28%] | 10% | PASS | PASS |
| HTTP lifecycle, time to ready | 24 | 4.72 ms → 4.81 ms (`time_to_ready_ms`) | +5.14% [−17.35%, +22.13%] | 10% | INCONCLUSIVE | **INCONCLUSIVE_DISCLOSED** |
| HTTP batch, size 1 | 24 | 171.405 ms → 167.780 ms (`window_duration_ns`) | +0.04% [−5.57%, +5.32%] | 10% | PASS | **UNRESOLVED** |
| HTTP batch, size 8 | 24 | 28.566 ms → 28.264 ms (`window_duration_ns`) | −0.42% [−5.05%, +8.17%] | 10% | PASS | PASS |
| HTTP batch, size 64 | 24 | 6.687 ms → 6.096 ms (`window_duration_ns`) | −2.11% [−4.01%, +1.96%] | 10% | PASS | **UNRESOLVED** |
| HTTP batch, size 256 | 12 | 2.941 ms → 2.908 ms (`window_duration_ns`) | −1.72% [−3.13%, +6.84%] | 10% | PASS | PASS |

## Gated supporting metrics

| Cell | Metric | v0.4.0 median | v0.5.0 candidate median | Paired change | Interval | Tolerance | Status |
|---|---|---|---|---|---|---|---|
| Core sparse traversal, 10k, `compact-bfs` | `connected_p99_ns` | 50.8 µs | 40.0 µs | −11.33% | [−22.48%, +0.66%] | 25% | PASS |
| Core sparse traversal, 10k, `compact-bfs` | `peak_rss_bytes` | 5.55 MB | 5.59 MB | +0.29% | [+0.29%, +0.88%] | 20% | PASS |
| Core sparse traversal, 10k, `compact-workspace` | `connected_p99_ns` | 46.1 µs | 46.7 µs | +1.06% | [−8.97%, +5.00%] | 25% | PASS |
| Core sparse traversal, 10k, `compact-workspace` | `peak_rss_bytes` | 5.55 MB | 5.59 MB | +0.59% | [+0.29%, +0.88%] | 20% | PASS |
| Core sustained churn, 10k, `compact-bfs` | `connected_p99_ns` | 5.1 µs | 5.1 µs | +1.22% | [−2.46%, +5.13%] | 25% | PASS |
| Core sustained churn, 10k, `compact-bfs` | `peak_rss_bytes` | 5.56 MB | 5.57 MB | +0.29% | [+0.00%, +0.59%] | 20% | PASS |
| Core sustained churn, 10k, `compact-workspace` | `connected_p99_ns` | 4.4 µs | 4.4 µs | +0.47% | [−1.86%, +1.88%] | 25% | PASS |
| Core sustained churn, 10k, `compact-workspace` | `peak_rss_bytes` | 5.58 MB | 5.57 MB | +0.15% | [−0.29%, +0.30%] | 20% | PASS |
| HTTP lifecycle, time to ready | `query_latency_p99_ns` | 165.2 µs | 170.6 µs | +6.66% | [−4.27%, +17.37%] | 25% | PASS |
| HTTP lifecycle, time to ready | `sampled_max_rss_bytes` | 8.02 MB | 7.96 MB | +0.31% | [−0.61%, +1.47%] | 20% | PASS |
| HTTP batch, size 1 | `request_latency_p99_ns` | 119.4 µs | 132.6 µs | +6.04% | [−27.84%, +50.04%] | 25% | INCONCLUSIVE |
| HTTP batch, size 1 | `sampled_max_rss_bytes` | 7.39 MB | 7.60 MB | +0.55% | [−0.43%, +3.79%] | 20% | PASS |
| HTTP batch, size 8 | `request_latency_p99_ns` | 162.4 µs | 166.7 µs | −1.01% | [−8.80%, +7.35%] | 25% | PASS |
| HTTP batch, size 8 | `sampled_max_rss_bytes` | 7.26 MB | 7.33 MB | +0.22% | [−2.79%, +2.97%] | 20% | PASS |
| HTTP batch, size 64 | `request_latency_p99_ns` | 214.5 µs | 200.3 µs | −3.78% | [−11.93%, +3.64%] | 25% | PASS |
| HTTP batch, size 64 | `sampled_max_rss_bytes` | 6.94 MB | 7.03 MB | +0.11% | [−3.50%, +25.14%] | 20% | INCONCLUSIVE |
| HTTP batch, size 256 | `request_latency_p99_ns` | 275.6 µs | 287.0 µs | +3.48% | [−4.75%, +20.36%] | 25% | PASS |
| HTTP batch, size 256 | `sampled_max_rss_bytes` | 7.04 MB | 6.79 MB | −0.12% | [−17.70%, +15.90%] | 20% | PASS |

## Report-only metrics

| Cell | Metric (report only) | v0.4.0 median | v0.5.0 candidate median |
|---|---|---|---|
| Core sparse traversal, 10k, `compact-bfs` | `link_p99_ns` | 42 ns | 42 ns |
| Core sparse traversal, 10k, `compact-bfs` | `cut_p99_ns` | 42 ns | 42 ns |
| Core sparse traversal, 10k, `compact-workspace` | `link_p99_ns` | 42 ns | 42 ns |
| Core sparse traversal, 10k, `compact-workspace` | `cut_p99_ns` | 42 ns | 42 ns |
| Core sustained churn, 10k, `compact-bfs` | `link_p99_ns` | 42 ns | 42 ns |
| Core sustained churn, 10k, `compact-bfs` | `cut_p99_ns` | 42 ns | 42 ns |
| Core sustained churn, 10k, `compact-workspace` | `link_p99_ns` | 42 ns | 42 ns |
| Core sustained churn, 10k, `compact-workspace` | `cut_p99_ns` | 42 ns | 42 ns |

These are not classified: timer resolution: medians are within two ticks (41.67 ns) of the host timer, so one tick is a 100% change; no percent bound is established.

## Missing coverage and changes in semantics

- **Unmeasured release to release** (no inference is made about them): the
  `ett` and `hdt` engines; `/metrics` on; source-managed mode and feeder
  traffic; other hosts, operating systems and CI-built binaries.
- **Node and edge lifecycle** (opt-in, new in v0.5.0) has no v0.4.0
  counterpart, so it cannot be compared release to release. Its cost was
  measured against semantically equivalent references on `compact-bfs`
  (61 timed cells: 56 PASS, 2 REGRESSION, 3 INCONCLUSIVE; memory: 3 heap-growth
  FAILs under fresh-ID churn), all accepted by maintainer waivers for v0.5.0
  only. Absolute values per cell: [run4-bc-analysis.md](run4-bc-analysis.md);
  summary: [RUN-4-dcd8ccc.md](RUN-4-dcd8ccc.md).
- **Methodology:** identical to the v0.4.0 qualification (same nine workloads,
  harness, collector and rules), so the outcomes are directly comparable to
  the v0.4.0 column of the product's *Performance by version* page. Do not
  chain releases: each campaign compares one release with its predecessor.

## Dispositions

- **UNRESOLVED, waived for v0.5.0:** HTTP batch size 1 request p99 (+6.04%,
  interval upper bound +50.04% against 25%); HTTP batch size 64 sampled maximum
  RSS (+0.11%, upper bound +25.14% against 20%).
- **INCONCLUSIVE_DISCLOSED, acknowledged:** HTTP time to ready (+5.14%, upper
  bound +22.13% against 10%).
- No improvement is claimed: no cell has a passing primary metric with an
  interval entirely below zero.
- Earlier candidates' experiment-A results (`6494253`, `a1d9577`) are kept
  separately and are not selected across candidates.

## Raw evidence

- Private repository `knotrel/knotrel-qualification-evidence`, package commit
  `83ec5474b62d9506352e93a95cf54069826052d7`, directory `v0.5.0/` (access on
  request; see [evidence/INVENTORY.md](evidence/INVENTORY.md)).
- This campaign: `v0.5.0-qualification/A-20261116T113709Z-dcd8ccc/` inside
  `knotrel-v0.5.0-evidence.tar.gz`
  (sha256 `13e136056d20ee96fcfb534819e1ac10fc85238a54b56b5e8af2dcd0e4c5dce7`);
  executables in `knotrel-v0.5.0-measured-executables.tar.gz`
  (sha256 `b717703c9abaf9d7bff1392e1c8435bee345db316f65953e57d0ad2d2ddbce53`);
  checksum manifest `MANIFEST.sha256`
  (sha256 `4c30bf09aa93d98c6a50eaab04a86111015306ae600d61db7f875925537e3adb`).
- Raw pair inputs: main manifest sha256
  `66ad1a992576fc467770197aec6b3731566945eff1ad3047369dcab59ce1252c` (108 pair files),
  extension manifest sha256 `70b2a20d15a581a32c8816bcb12502357c21c4a55baaa1d951ca0b92db07992b`
  (48 pair files).

## Reproduction

Use both repository revisions explicitly: knotrel `556683c8beb1ffe90fbf645bcf7955880690df2c` (B)
and `dcd8ccca10ef5766e3c9252832594186bf93bbc3` (C), knotrel-benchmarks `df635a1e872fd9e2d556b166ac23f342ee45d675` for
the harness, and this repository at tag `v0.5.0` for the collector, analysis
and protocol ([PROTOCOL.md](PROTOCOL.md), amendment 4). A sibling path
dependency is not pinned by either tag.
