# Knotrel v0.6.0 qualification protocol

**Status: DRAFT until `FREEZE.json` exists in this directory.** The
machine-readable definition is [`MATRIX.json`](MATRIX.json); this file explains
it. Nothing here was chosen after seeing a final result. Diagnostics (budget
3 h, `evidence/v0.6.0-diagnostics/`) decide which optimization candidates are
retained; they never change a final verdict.

## 1. References and identities

| Role | Identity |
|---|---|
| Product reference | knotrel **v0.5.0, published** (crates.io 0.5.0, GitHub Release, signed tag `v0.5.0` = `51e3b4da2de802a4ebf352b1e8a8311657e48d38`) |
| Benchmarks reference | knotrel-benchmarks tag `v0.5.0` = `7ce6abb726ef3112604df2ceaff7b4a7ef21c328` |
| Candidate | knotrel `feature/v0.6.0-lifecycle-efficiency` at the frozen commit recorded in `FREEZE.json` |
| Tooling | knotrel-benchmarks `feature/v0.6.0-qualification` at the frozen commit recorded in `FREEZE.json` (probes, collectors, analyses) |
| Toolchain | rustc 1.100.0, release profile, `--locked` (derived lockfiles where a probe links two knotrel versions; each derivation is recorded as a diff) |
| Host | Apple M3, macOS 26.5.2; AC power, no recorded thermal or performance warning, no concurrent build or campaign, `caffeinate -dimsu` |

Product and benchmark identities are recorded separately; every probe prints
the knotrel commit and dirty state it was built from, and analyses reject a
build that does not name the expected clean commit.

## 2. Experiments

| Exp. | Question | Design | Rules |
|---|---|---|---|
| **A** | Lifecycle off: did existing behavior regress against v0.5.0? | The nine v0.4.0/v0.5.0 cells (core traversal and churn on `compact-bfs`/`compact-workspace`, HTTP batch 1/8/64/256, startup), 12 pairs in three seeded sessions (130600–130602), fresh processes, balanced order; one extension (130610–130612) | v0.4.0 rules unchanged: primary 10%, p99 25%, RSS 20%; INCONCLUSIVE_DISCLOSED / UNRESOLVED as defined there |
| **B/C** | Lifecycle cost and sustained resources on the candidate | v0.5.0 run 4 cells and window multipliers unchanged, `compact-bfs` scope, order seed 50600 | v0.5.0 protocol §3–4 unchanged (25/50/100/6%, B5 3.0×, C1–C4); no extension, no rerun |
| **R** | Lifecycle on: candidate vs v0.5.0 on imports and churn | `release-cells` built against each release; 11 cells (core and HTTP flagged imports at 10k/100k with 20/10 and 60/30 flags, hub; fresh/same/toggle churn at 100k); 2 warmup + 12 analyzed pairs, a fresh process per observation, order balanced, seed 60500 | primary 10%; IMPROVED reported only when the interval's upper bound is below 0 |
| **Rmem** | Lifecycle on: memory peaks candidate vs v0.5.0 | `memory-peak` (allocator byte counts, deterministic), 10 runs per arm | REGRESSION if candidate > 1.20 × reference |
| **M_desc** | Contention profile of the candidate | `contention-probe` against a real server process: standalone {lifecycle off, on} × {10k, 100k} × mixes {read95, mixed50, lifecycle50 (on only)} × batch {1, 8, 64} × clients {1, 4, 16, 64}; source-managed read-only clients {4, 16, 64} × background {none, replace import every second, feeder catch-up}; open-loop at 0.5/0.9/1.1 × measured saturation | Descriptive; feeds the predeclared M5 rule (design §6) |
| **M_reg** | Contention regression against v0.5.0 | 6 fixed configurations, 2 warmup + 12 pairs, fresh server per observation, order balanced, seed 60600 | throughput 10% (B/C ratio), client p99 25% |

Known asymmetries and omissions, disclosed with the results: R and M_reg
compare the same workload on two releases, so they measure end-to-end change,
not the cause; M_desc has no reference arm; the experimental `ett`/`hdt`
engines have no lifecycle cells (lifecycle is rejected for them) and only the
A cells cover their non-lifecycle use indirectly (`compact-workspace` is a
harness variant of `compact-bfs`); feeder and import paths with lifecycle off
have no release-to-release cell except through M_reg's source-managed cells.

## 3. New thresholds

R and M_reg reuse the approved v0.4.0 tolerances for existing operations
(lifecycle operations and imports are existing operations since v0.5.0):
primary 10% for times and throughput, 25% for tails. Rmem applies the 20%
memory tolerance (approved for RSS) to deterministic heap byte counts. These
applications were presented to the maintainer once before measuring; the
record is in `FREEZE.json`.

## 4. Validity, invalidation and budget

- Host checks before every child (collector) and before each experiment (no
  build processes). A failed check stops the experiment; the partial output
  is kept and reported as invalid.
- Collectors refuse to overwrite an output directory. Invalid runs stay
  recorded. One rerun per experiment only for an infrastructure failure
  unrelated to the measured code, with its cause recorded. No rerun until
  favorable, no selected seeds or layouts, no outlier exclusion.
- After freezing, a change to executed knotrel code invalidates every
  experiment that measured it (documentation-only commits are checked by
  comparing `__TEXT,__text` of release builds); a tooling change invalidates
  the affected experiment.
- Estimated final runtime: about 83 minutes (A 27, B/C 8, R 12, Rmem 2,
  M_desc 16, M_reg 18). Cap 4 hours; the maintainer is asked first if a
  revised estimate exceeds it.

## 5. Claims

Results apply to the measured host, toolchain, configurations and workloads.
No general speedup is claimed; an improvement is claimed only for a cell whose
interval lies entirely below zero. Absolute values accompany every percentage.
