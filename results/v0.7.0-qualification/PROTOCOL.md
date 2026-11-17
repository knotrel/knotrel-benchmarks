# Knotrel v0.7.0 qualification protocol

**Status: DRAFT until `FREEZE.json` exists in this directory.** The
machine-readable definition is [`MATRIX.json`](MATRIX.json); this file explains
it. It is the v0.6.0 protocol
([`../v0.6.0-qualification/PROTOCOL.md`](../v0.6.0-qualification/PROTOCOL.md))
with the reference moved to published v0.6.0; the differences are listed in
§3. Nothing here was chosen after seeing a final result. Diagnostics
([`diagnostics/DIAGNOSTICS-v0.7.0.md`](diagnostics/DIAGNOSTICS-v0.7.0.md))
decided which candidates are qualified; they never change a final verdict.

## 1. References and identities

| Role | Identity |
|---|---|
| Product reference | knotrel **v0.6.0, published** (crates.io 0.6.0, signed tag `v0.6.0` = `5db9ec4738a7f90bf06a83ea12f35c0dab9ab538`) |
| Benchmarks reference | knotrel-benchmarks tag `v0.6.0` = `bddef0f301f582495cb22e47cfd67def88fa9967` (reference probe lockfile) |
| Candidate | knotrel `feature/v0.7.0-measured-concurrency` at the frozen commit recorded in `FREEZE.json`: 0.7.4a shared read lock, 0.7.4b `sonic-rs` import parse |
| Tooling | knotrel-benchmarks `feature/v0.7.0-qualification` at the frozen commit recorded in `FREEZE.json` |
| Toolchain | rustc 1.100.0, release profile, `--locked --offline` (derived lockfiles recorded as diffs) |
| Host | Apple M3, macOS 26.5.2; AC power, no thermal or performance warning, no concurrent build or campaign, no IDE or `git` process, `caffeinate -dimsu` |

## 2. Experiments

Unchanged from v0.6.0 in cells, workloads, pair counts, warmups, windows and
rules; new seeds.

| Exp. | Question | Rules |
|---|---|---|
| **A** | Lifecycle off: did existing behavior regress against v0.6.0? Nine cells, 12 pairs in three seeded sessions (130700–130702), one extension (130710–130712) | v0.4.0 rules: primary 10%, p99 25%, RSS 20%; INCONCLUSIVE_DISCLOSED / UNRESOLVED as defined there |
| **B/C** | Lifecycle cost and sustained resources on the candidate (v0.5.0 run 4 cells, order seed 50700) | v0.5.0 protocol §3–4 unchanged |
| **R** | Lifecycle on: candidate vs v0.6.0, 11 import and churn cells, 2 warmup + 12 pairs (order seed 60700) | primary 10% |
| **Rmem** | Lifecycle on: memory peaks, 10 cells, one run per arm | REGRESSION if candidate > 1.20 × reference |
| **M_desc** | Contention profile of the candidate: the v0.6.0 156 configurations and open loop | Descriptive; validity rule (§3); M5 rule (i) re-evaluated descriptively |
| **M_reg** | Contention regression against v0.6.0: the six v0.6.0 cells, 2 warmup + 12 pairs, fresh server per observation (order seed 60701) | throughput 10%, client p99 25%; INVALID if any analyzed observation fails the validity rule |

## 3. Differences from the v0.6.0 protocol

1. **Reference** is published v0.6.0 (was v0.5.0).
2. **Contention probe revision 2** (the fixed probe of the v0.6.0 M
   supplement) for M_desc and M_reg, with its validity rule: a configuration
   is VALID only with no transport errors, no per-item errors, no no-op
   mutations and, with background activity, no background failure and at
   least one completed background unit. 503 refusals are allowed and
   reported.
3. **M_desc layout:** the same 156 configurations, but `mixed50`
   configurations run on their own fresh server per kind, and each
   `lifecycle50` configuration on its own fresh server (revision 2 toggles
   base items for `lifecycle50`). 36 server processes instead of 8.
4. **Activity gate:** `host_activity_monitor.py --check` (no Antigravity IDE,
   Visual Studio Code or `git` process) before the chain and before every R,
   Rmem and M child; a continuous monitor samples the whole chain. This adds
   the v0.6.0 M-rerun conformance check to the frozen host checks.
5. **No inherited waivers:** every v0.6.0 non-PASS result is re-measured
   and reported as measured; the v0.6.0 maintainer acceptances do not apply.

Thresholds are unchanged from v0.6.0 (maintainer, 2026-11-17: "thresholds as
in v0.6.0 unless the maintainer changes them").

## 4. Validity, invalidation and budget

As in v0.6.0 §4. After freezing, a change to executed knotrel code invalidates
every experiment that measured it (documentation-only commits are checked by
comparing `__TEXT,__text` of release builds); a tooling change invalidates the
affected experiment. Estimated runtime about 86 minutes (A 27, B/C 8, R 12,
Rmem 2, M_desc 19, M_reg 18); cap 4 hours.

## 5. Claims

Results apply to the measured host (ARM64), toolchain, configurations and
workloads. No general speedup is claimed; an improvement is claimed only for a
cell whose interval lies entirely below zero. Absolute values accompany every
percentage. `sonic-rs` performance on x86-64 is not measured.
