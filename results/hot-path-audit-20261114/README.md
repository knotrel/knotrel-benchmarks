# Hot-Path Audit Campaign (knotrel v0.3.0 candidate)

Hand-written narrative for the campaign. Every number below is taken from the
generated [REPORT.md](REPORT.md) and [analysis/summary.json](analysis/summary.json),
which [analyze.py](analyze.py) regenerates from the raw artifacts in [run/](run/).
If this file and the generated report ever disagree, the generated report wins.

## Purpose

The Knotrel hot-path audit (`docs/hot-path-audit-v0.3.0.md` in the `knotrel`
repository) changed allocation, cloning, lookup and contention behaviour on
the request, mutation, query, import and feeder paths of `knotrel-core` and
`knotrel-server`, without changing any client-visible contract. This campaign
measures that change set once, on the official toolchain, against its exact
baseline, with a same-binary A/A arm, so that the audit document can cite
reproducible evidence instead of the earlier screening runs.

The campaign answers three questions:

1. Are results identical? (correctness across arms)
2. How many heap allocations does each request make? (deterministic counts)
3. Which timing changes exceed the A/A noise of this host? (confirmed,
   regressed or inconclusive)

## Identities and provenance

| Item | Value |
| --- | --- |
| Baseline | knotrel `e1e11818a762baf07575719456a2158959b2e2c8` (HEAD of `refactor/typed-constants`), materialized with `git archive` |
| Candidate | baseline + [run/candidate/candidate-code.patch](run/candidate/candidate-code.patch) (10 files under `crates/`) |
| Candidate code identity | `git diff HEAD -- . ':(exclude)docs' \| shasum -a 256` = `8b579f7d8a8db52d499263870b486d0bbaec1775135c4bb50f8e9005a55cc9d7` |
| knotrel-benchmarks | `main` at `5ac5b76bcce4323a83f20173de63212805b1fbb8`, clean tracked files; the campaign tools were untracked when measured |
| Toolchain | Rust 1.100.0 (`0ef1bc386`) for every build |
| Host | Apple M3 (Mac15,12, 4P+4E cores, 16 GiB), macOS 26.5.2, AC power, no thermal warning |
| Collected | 2026-11-15, 07:14–07:35 UTC, 557 observations |

The collector refuses to run unless knotrel HEAD is the baseline commit and
the working tree's code diff hash equals the value above; it records the
staged and unstaged state (the index equalled the working tree). It then
materializes both arms as immutable trees (`git archive` of the baseline, plus
`git apply` of the archived patch for the candidate) and checks that every
candidate file matches the working tree byte for byte
([run/candidate/reconstruction.json](run/candidate/reconstruction.json)).
The candidate binaries are therefore built from the same sources as the
working tree, not from the live checkout.

**Link to the verified final tree.** The audit's final tree was verified on
2026-11-14 under the identity `git diff` (index to working tree) =
`b17d7018523f2e0a6a40f3a4ef19d9ce9c2b29feeabf7a5027e946d1b920ea36`. Since then
the user staged every change, so that hash can no longer be recomputed
directly. [provenance/reconstruct_verified_tree.sh](provenance/reconstruct_verified_tree.sh)
rebuilds the verification-time index (blobs listed in
[provenance/verification-time-index.txt](provenance/verification-time-index.txt))
and working tree in a throwaway clone, substituting the archived
verification-time copy of the audit document
([provenance/verification-time-docs/](provenance/verification-time-docs/)),
and prints `MATCH`:

```sh
bash results/hot-path-audit-20261114/provenance/reconstruct_verified_tree.sh ../knotrel
```

It matched when this README was written. Only `docs/hot-path-audit-v0.3.0.md`
changed after verification, so the measured candidate code is the verified
final code. In particular, the cached HTTP metric handles reverted during the
review are **not** part of the candidate.

## Layout

| Path | Content |
| --- | --- |
| [REPORT.md](REPORT.md) | Generated report: identities, host, verification, correctness, allocation counts, verdict tables, microbenchmarks, end-to-end section |
| [analysis/summary.json](analysis/summary.json) | Per-cell statistics, every allocation repeat, paired changes, verdicts |
| [analysis/observations.csv](analysis/observations.csv) | One normalized row per metric value |
| [manifest.json](manifest.json) | Size, sha256 and description of every artifact in this directory |
| [analyze.py](analyze.py), [tests/](tests/) | Analysis and its unit tests |
| [run/](run/) | Raw collector output: `collector.log`, `DONE`, `provenance.json`, `environment.json`, `host-checks.jsonl`, `schedule.json`, `observations.jsonl`, child streams under `raw/`, build logs under `builds/`, repository verification logs under `verification/` |
| [provenance/](provenance/) | Proof linking the measured candidate to the verified final tree |

Measurement code lives outside this directory:
[scripts/run_hot_path_audit.py](../../scripts/run_hot_path_audit.py) (collector,
tests in `scripts/tests/test_hot_path_audit.py`) and
[tools/hot-path-probes/](../../tools/hot-path-probes/README.md) (router probe and
mechanism microbenchmarks).

## Reproduction

Prerequisites: the sibling `knotrel` checkout at the baseline commit with the
candidate code in its working tree (staged or not; the identity uses
`git diff HEAD`), Rust 1.100.0 installed through rustup, Python 3 (used:
3.12), and a quiet host on AC power. From `knotrel-benchmarks`:

```sh
python3 scripts/run_hot_path_audit.py <new-output-directory>
```

The collector writes `<new-output-directory>/run/` and refuses to overwrite an
existing `run/`. It verifies provenance, builds both arms, runs the repository
verification, the correctness and allocation passes, 12 counterbalanced timed
rounds and the separate end-to-end section, and ends with `run/DONE` (or
`run/STOPPED` with the reason). Copy `analyze.py` and `tests/` next to the new
`run/` to analyze it.

Regenerating this campaign's derived files from the archived raw data needs
only Python:

```sh
python3 results/hot-path-audit-20261114/analyze.py          # rewrite outputs
python3 results/hot-path-audit-20261114/analyze.py --check  # verify byte-identical regeneration
```

`analyze.py` verifies the sha256 of every archived child stream before
parsing it, and its outputs do not depend on the time of analysis (fixed
bootstrap seed 20261115).

## Method

- **Arms.** `base`, `cand`, and `aa`, a byte-identical copy of the baseline
  binaries under another path. Each round runs every cell once per arm in a
  counterbalanced order (all six orders equally often), 12 rounds in two
  sessions, with 60 s quiet before the first session, 120 s between sessions
  and 5 s between rounds. The schedule is in [run/schedule.json](run/schedule.json).
- **Cells.** Core bulk initialization (`initialization-profile`,
  `facade-limited` surface, which is the server's import path) and dynamic
  link/cut/connected workloads (`knotrel-benchmarks`) for `compact-bfs`,
  `ett-scan` and `hdt` on two workloads each, plus the in-process router probe
  in six scenarios with metrics off and on.
- **Router probe.** Drives the complete `knotrel-server` router through
  `tower::ServiceExt::oneshot`: extractors, middleware, worker admission, the
  blocking job and response construction, with no sockets. Timing builds use
  mimalloc, like the server.
- **Statistics.** Each process yields one value per metric (the median of its
  internal repetitions, never the fastest). For each round the candidate and
  A/A values are compared with the baseline of the same round as a percent
  change (positive = slower). The paired median and a 95% percentile
  bootstrap interval (10,000 resamples) summarize them. The A/A bound is the
  larger magnitude of the A/A interval's endpoints. A change is **confirmed**
  only if its interval excludes zero **and** its median magnitude exceeds the
  A/A bound; anything else is **inconclusive**. The exact two-sided sign test
  is reported for information only; it is not part of the verdict.

## Deviations and caveats

- **License boundary.** The router probe links `knotrel-server`, which is
  licensed under Elastic-2.0. It therefore lives in `tools/hot-path-probes/`,
  a standalone Cargo workspace with its own `Cargo.lock`, so the Apache-2.0
  root workspace, its lockfile and its cargo-deny policy are unchanged. The
  probe source is Apache-2.0; binaries built from it include Elastic-2.0 code
  and are for local measurement only.
- **Counting allocator.** Allocation counts come from a separate build of the
  probe (`--features count-alloc`) that replaces mimalloc with the system
  allocator wrapped by `stats_alloc`. Counts are allocations plus
  reallocations per request inside the timed window. They are deterministic
  for single-threaded scenarios; concurrent scenarios vary slightly with
  background runtime work (largest spread 0.074%). **Allocation counts are not
  timings**, and timings from the counting build are never reported.
- **End-to-end HTTP.** `measure_e2e --scenario lifecycle --dataset large`
  against each arm's release server (mimalloc, loopback TCP,
  `Connection: close`), 6 rounds with an A/A arm. TCP connection setup can
  dominate request timings, and 6 rounds give wide intervals. It is a separate
  section and is never combined with in-process results. The verdict column
  applies the slower-is-positive rule mechanically; for `query_qps` a
  positive change is an improvement.
- **Multiple comparisons.** The campaign reports 42 in-process timing tests
  and 9 end-to-end tests without a family-wise correction. The A/A bound
  guards against, but does not eliminate, false discoveries: with this many
  tests, one or two marginal verdicts are expected by chance. Verdicts whose
  median barely exceeds the bound should be read with that in mind (see the
  regression below).
- **Joint effects.** Every candidate change is measured together. Timing
  changes are not attributed to individual changes; no per-change ablation
  was run in this campaign.
- **Mechanism microbenchmarks** (`job-tracking`) replicate server patterns in
  isolation and do not call Knotrel code. They explain mechanisms; they are
  not request-level effects.
- **Single host.** One Apple M3 laptop. The results do not transfer to other
  hosts without re-measurement.

## Findings

**Correctness.** Trace fingerprints are identical across arms for all 12
timed core cells; the initialization dynamic-continuation oracle passed 12/12;
router response digests are identical between baseline and candidate for
12/12 scenario and metrics combinations; end-to-end oracle agreement was
100% in 18/18 runs. Every timed observation exited 0.

**Allocation counts per request** (metrics off; metrics on in REPORT.md):

| Scenario | Baseline | Candidate | Change |
| --- | ---: | ---: | ---: |
| Single `connected` | 96 | 80 | −16.7% |
| 8 concurrent clients, single `connected` | 95.01 | 79.04 | −16.8% |
| Batch, 1,024 `connected` | 5,223 | 3,161 | −39.5% |
| Batch, 1,024 alternating cut/link | 3,175 | 1,113 | −64.9% |
| Import, 100,000 nodes and 99,999 edges | 400,152 | 100,127 | −75.0% |
| Feeder batch, 1,024 events | 10,358.76 | 4,189.53 | −59.6% |

**Confirmed improvements (13).** Router probe, metrics off: batch
`connected` −7.87%, batch cut/link −9.46%, feeder batch −14.28%, import
−21.13%; metrics on: −6.42%, −9.14%, −18.59%, −21.59%. Core initialization:
`compact-bfs` chain −6.30% and blocks −7.32%, `ett-scan` blocks −3.87%, `hdt`
blocks −4.00%. Dynamic: `ett-scan` blocks `link_total_ns` −3.54% (equal to its
A/A bound to two decimals; marginal). Intervals and bounds are in REPORT.md.

**Confirmed regression (1), likely spurious.** Dynamic `compact-bfs`
sustained-churn blocks `connected_total_ns`: +2.14% [+0.64%, +4.18%] against
an A/A bound of ±2.06% (sign test p = 0.039). No code on the `compact-bfs`
`connected` query path changed: the patch only adds `Graph::contains_node`,
used by the limited facade's limit checks. The same cell's
`workload_wall_ns` is inconclusive (+1.76%, bound ±2.22%), and its `link` and
`cut` totals moved in the faster direction (inconclusive). With 42 tests and a
margin of 0.08 percentage points over the bound, this is consistent with a
chance or code-layout effect, but it is reported as measured and is not
dismissed. Re-measure this cell before claiming either direction.

**Inconclusive (28).** Notably the single-request router scenarios (single
`connected` and 8 concurrent clients, both metrics settings), which are below
the A/A noise at about 7 µs per request despite 16 fewer allocations;
`ett-scan` and `hdt` chain initialization; and all `hdt` and most `ett-scan`
dynamic totals.

**End-to-end.** `sampled_max_rss_mib` is lower in the candidate: −4.66%
[−8.95%, −3.47%] against an A/A bound of ±4.50% (marginal), consistent with
the import releasing its body buffer before building the graph. Import,
catch-up, time-to-ready, query QPS, latency p50/p95, final RSS and restart
recovery are inconclusive.

**Mechanisms** (median ns/op): outstanding-job track/release 83.01 (`watch`)
versus 7.26 (atomic plus `Notify`) on one thread, 879.85 versus 104.08 with
four threads; 1 MiB body copy 17,583 versus 74 for converting a uniquely owned
buffer; one millisecond clock read 20.38; metric-family `get_or_create` 63.13
versus 1.87 for a cached handle (the cache is reverted and not in the
candidate; this row documents why the mechanism alone did not justify it).
