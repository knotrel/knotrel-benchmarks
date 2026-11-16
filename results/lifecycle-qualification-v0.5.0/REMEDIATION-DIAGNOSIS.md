# v0.5.0 remediation — diagnosis record

Scope: the run-2 failures of candidate `6494253` (C3 heap growth, B4 flagged
import, B3 high-degree removal). Run-2 verdicts are unchanged and remain the
record for `6494253`. All diagnostics below were frozen before execution
(`D1-PLAN.md`, `D2-PLAN.md`, `D3-PLAN.md`) and changed no verdict.

## 1. Sustained memory (C3)

### Mechanisms, classified

| # | Mechanism | Where | Status | Bound |
|---|---|---|---|---|
| M1 | Emptied `BTreeSet` keeps its root leaf (104 B for `usize` keys); one set per vertex, so retained leaves tracked every vertex that ever held an incidence | `ett` non-tree sets; `hdt` per-level tree and non-tree sets | **Defect, fixed** (`1ec2de3`) | Before: up to one leaf per vertex per set. After: storage follows live incidences. |
| M2 | `hdt` upper-level vertex records were never released after becoming isolated singletons without incidences; records tracked the history of promoted vertices | `hdt` levels ≥ 1 | **Defect, fixed** (`1ec2de3`, review follow-up `9467e0a`) | Before: up to V records per level, growing with history (L3 on 100k sparse toggle: live records ~20-23k flat while isolated records grew 6k → 19k → 32k over cycles 10/20/30). After: slots ≤ peak live records per level, reused. |
| M3 | Live HDT level structure: spanning-forest copies of promoted tree edges and live exact-level incidences | `hdt` | **Inherent to HDT (also in the reference arm)** | O(V log V) logical: ≤ ⌊log₂V⌋+1 levels, each ≤ V records and ≤ 2(V−1) edge tokens. Measured steady state at engine level: 84.5 MiB → 186.7-187.6 MiB (cycles 80-120, 100k sparse toggle), per-level tree-edge counts stationary. |
| M4 | Vector capacity high-water (power-of-two growth of per-level arenas) | `hdt` arenas, all vectors | Bounded retention | Capacity ≤ 2 × peak length. Visible as discrete steps (e.g. +16 MiB when an L2 arena doubled). |
| M5 | `hashbrown` delete/insert churn at > 50% load: tombstone exhaustion forces one table doubling instead of an in-place rehash | `ett` engine edge map (+10.5 MiB at 100k), lifecycle catalog on fresh IDs (+5.2 MiB), reference maps | Bounded retention (library policy) | At most one doubling at constant item count. |
| M6 | Retired engine slots for removed nodes until compaction | facade, `fresh` schedules | By design | Engine vertices ≤ 2V + 1024; compaction restores; sawtooth. |

Lifecycle catalog: heap flat under toggle on every engine (compact-bfs toggle
slope exactly 0); not a growth source.

### Evidence

- D1-emptyset / D1-release (90 C-heap cells, run-2 argv, deterministic heap):
  no cell worse than run 2; all logical counts correct. Examples, 30-cycle
  final heap: `ett` ring toggle 60.5 → 54.6 MiB (flat); `hdt` sparse toggle
  225.2 → 182.3 MiB; `hdt` sparse fresh 250.3 → 189.1 MiB.
- D2 (120 cycles, frozen classification rule): all 14 `same`/`toggle` cells
  PLATEAU, all 3 compact-bfs `fresh` cells BOUNDED_SAWTOOTH, counts correct.
- Regression tests: `isolating_churn_releases_and_reuses_upper_level_records`
  and the record invariant `validate_records` (fails on the old code in four
  HDT tests); probes `tests/engine_storage_release.rs` (allocation-level,
  fails on the old code: +212,888 B over 2,047 fresh vertices).
- Independent review of `1ec2de3`: no blocker or major; 4 minor addressed in `9467e0a`.

### Residual against the frozen C3 rule

The frozen C3 slope test fits a line over cycles 1-30; HDT reaches its level
structure steady state after a transient of roughly 8-20 cycles (and needs
several edge lifetimes, ~20 cycles each at 5% churn, for `same`). The rule is
not changed. Requalified C3 verdicts are reported as measured.

## 2. Import comparison (B4)

See `D3/D3a.txt` (measured on `9467e0a`, before `7f19b11`; unpaired sequential
arms, medians of 15, one run, noise about ±0.1-0.3 ms) and the independent
methodology review.

Attribution. `D3-PLAN.md`'s first rule (information = `plain-all − plain-eff`)
overstates the information difference: it includes building engine edges that
neither solution needs. The corrected split of the gap G = `lc-flag −
plain-eff` uses P = (`plain-all − plain-eff`) − (`engine-all − engine-eff`) for
parsing and validating the non-effective entries, C = `lifecycle-build −
engine-eff` for catalog and core build, and R for the remainder (flagged-form
parsing, spec copies, noise):

| Cell (10k) | G | P (information) | C (catalog/core) | R |
|---|---|---|---|---|
| compact-bfs sparse 20/10 | 1.66 | 0.36 | 0.97 | 0.33 |
| compact-bfs hub 20/10 | 1.03 | 0.29 | 0.40 | 0.34 |
| compact-bfs sparse 60/30 | 2.42 | 1.00 | 0.91 | 0.51 |
| ett sparse 20/10 | 1.73 | 0.09 | 1.24 | 0.40 |
| ett hub 20/10 | 2.92 | 0.07 | 2.14 | 0.71 |
| ett sparse 60/30 | 2.38 | 0.88 | 0.94 | 0.56 |
| hdt sparse 20/10 | 2.27 | 0.35 | 1.19 | 0.73 |
| hdt hub 20/10 | 2.75 | 0.22 | 2.06 | 0.47 |
| hdt sparse 60/30 | 2.47 | 0.82 | 0.95 | 0.70 |

The information difference is a minority of the gap (about 20-40% with
60/30 flags, often under 25% with 20/10); the candidate's catalog and core
build is 40-75%. Part of C is contract work a capability-equivalent reference
would also pay (an incidence index and validation of every entry); part was
avoidable:

- `7f19b11` removed per-edge duplicate-map lookups and incident-vector
  growth/shrink reallocations: lifecycle build 1.40 → 1.22 ms (compact-bfs,
  20/10), 1.03 → 0.81 ms (60/30); HTTP flagged import 2.76 → 2.39 ms and
  2.74 → 2.22 ms.
- Engine insertion order (D3d, frozen rule): feeding the engine in payload
  order instead of `finish`'s sorted order is 36-41% faster on `ett`/`hdt` hub
  but 58% slower on `compact-bfs` hub and 8% slower on `hdt` sparse; the rule
  (no cell more than 2% slower) is not met, so the order is unchanged. Engine
  bulk construction is order-sensitive and no order dominates.

Omitted reference work: deriving the effective edge list (0.03-0.05 ms) was
untimed; corrected prospectively (amendment 2, probes `7ffadc9e`, `444806d3`).
Capability differences (disclosed, not corrected; both favor the reference):
the lean store has no per-node incidence index (later reactivation/removal is
an O(E) scan instead of O(degree)), validates nothing, uses dense IDs and has
no atomic publication. Untimed body serialization favors the candidate.
With 60/30 flags the contract's unavoidable parse of non-effective entries
alone (about 1.0 ms on compact-bfs) is about three times the 0.32 ms reference
import, so the 100% budget cannot be met there by any implementation of the
full-topology contract: an owner decision, not a tuning matter.

## 3. High-degree removal (B3)

`D3/D3b.txt`: catalog bookkeeping costs about the same in both arms
(candidate 0.6-4.3 ms, reference 0.4-4.8 ms per window). The remaining gap is
engine work that depends on cut order: on the star, the reference's
`FxHashMap` iteration order is cheaper for `ett`/`hdt` than descending order
(HDT 16384: 44.9 vs 66.5 ms engine-only).

`D3/D3c.txt` (frozen adoption rule): `FxHashMap` order is faster only on the
star; it is 1-27% slower on every generator (`sparse`, `ring`, `hub`) for both
engines. Rule not met: descending order stays. The B3 gap is engine cut-order
sensitivity on this synthetic structure, not lifecycle bookkeeping.
