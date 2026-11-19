# knotrel v0.7.0: qualification 3 protocol (draft until FREEZE.json is written)

**Status: DRAFT (review pending).** This protocol is frozen by `FREEZE.json` after its
independent review and before any collection. Collection is launched by the
maintainer, as before.

## 1. Why a third qualification

**Attempt a3-3** of the v0.7.0 re-qualification qualified candidate e75ff6a
under FREEZE-A3 revision 2. It was CONFORMING to the conformance protocol,
with non-PASS results:
- REGRESSION (B4 `import-high`);
- FAIL ×3 (C3);
- INCONCLUSIVE ×2 (B4 `ops` sparse 100k, B4 `metrics-ops`);
- INVALID (M_desc `read100-b8-c64-import`).

**a3-3 is preserved in full,** with its data, analyses and verdicts. Nothing
in this protocol re-labels it. It stays the qualification of e75ff6a.

**This campaign qualifies a new candidate** under rules the maintainer
decided on 2026-11-19, after diagnostics D1–D5 and D1b–D5b and the phase-3
verifications (`results/v0.7.0-requalification/diagnostics/`). Verbatim
decisions:
- **import:** "confermo il contratto di conservazione della topologia
  registrata completa. Autorizzo un riferimento futuro equivalente per
  capacità, validazione e garanzie. Mantieni anche L/E come confronto
  descrittivo del costo aggiuntivo. Nessun cambio di API ora."
- **ops:** "includi nella futura finestra della referenza il lavoro del
  planner necessario a offrire lo stesso servizio."
- **C3:** "Non spostare per ora la finestra dopo la prima compattazione:
  misuriamo sia il transitorio sia il regime."
- **metrics:** "Il budget resta al 6%."
- **probe:** "definisci un budget complessivo di tempo coerente con il
  workload, con backoff e limite ai tentativi. Esaurimento del budget e
  import non completati devono restare visibili."
- **general:** "mantenendo le soglie percentuali attuali. Conserva
  integralmente a3-3 e i suoi verdetti. … Non autorizzo un rilascio senza
  qualificazione conforme."

## 2. Candidate and reference

- **Reference:** knotrel v0.6.0 (signed tag `v0.6.0` =
  `5db9ec4738a7f90bf06a83ea12f35c0dab9ab538`), unchanged.
- **Candidate:** knotrel 0.7.0 at the commit recorded in `FREEZE.json`.
  It is e75ff6a plus the product changes that met their declared criteria
  in `DIAGNOSTICS-PLAN-3.md` (§2.1), and nothing else.

### 2.1 Product changes in the candidate

**Candidate: knotrel `fa5f3a9eac24873dd2d8d3e0a2c21764cfff9373`.** It is
`f34af87d` (the change), followed by `fa5f3a9` (comments, docs and the unit
test's rebuild counter only).

Its only code change since e75ff6a is the catalog tombstone handling in
`knotrel-core` (`crates/knotrel-core/src/topology.rs`, T1 of D2c). The other
commits on the branch are documentation.
- **The change:** an insert that would grow the lifecycle catalog's hash
  table rebuilds it at the same size instead, when live entries are at most
  90% of its full capacity.
- **Why it was adopted:** it met every criterion declared in
  `DIAGNOSTICS-PLAN-3.md` (§11):
  - C3 PASS in all topologies;
  - B5 unchanged;
  - lower peak;
  - rebuilds shorter than compactions;
  - tests pass;
  - B1 fresh-churn unchanged within ±0.5%;
  - the product reproduces the diagnostic byte for byte.

No metrics change (D4c unresolved) and no `ETag`-on-412 change (evaluation
only, no API change) are included.

## 3. Experiments, cells and thresholds

**Unchanged from the re-qualification** (`results/v0.7.0-requalification/
PROTOCOL.md` and `MATRIX.json`), except as stated here:
- experiments A, B/C, R, Rmem, M_desc and M_reg;
- their cells, pair counts and estimators;
- **every percentage threshold:** A primary 10%, query tail 25%, RSS 20%;
  B1/B2/B3/B4 cell tolerances; B5 3×; C1–C4; R, Rmem and M_reg tolerances;
- the M_desc validity rule, extended in §6.

**Seeds and workloads are a3-3's** (addendum 1, A5 of `DIAGNOSTICS-PLAN-3.md`):
- A session seeds 130720–130722 and extension seeds 130730–130732;
- the B/C, R and M_reg order seeds and the probe seeds;
- every workload.

The equivalent cells reuse their frozen counterparts' workloads, seeds and
request counts. Reusing the seeds reuses no data: a new campaign collects
everything anew.

**B/C run order** (`run_lifecycle_qualification.run_order`):
- the 127 frozen cells keep exactly a3-3's order (seed 50720, checked
  against a3-3's `plan/order.json` by a test);
- each equivalent cell runs immediately after its frozen counterpart.

## 4. Capability-equivalent B4 references

### 4.1 What decides and what is descriptive

Thirteen B/C cells are added (`run_lifecycle_qualification.py
--equivalent-references`), with the tolerance and request count of their
frozen counterpart:

| Equivalent cell (verdict) | Frozen counterpart (descriptive, no verdict) | Tolerance |
|---|---|---|
| `B4-http-import-high-equivalent-compact-bfs-sparse-10000` | `B4-http-import-high-…` (L/E) | 100% |
| `B4-http-import-equivalent-compact-bfs-{sparse,hub}-10000`, `…-sparse-100000` | `B4-http-import-…` | 100% |
| `B4-http-ops-equivalent-compact-bfs-{sparse,hub}-10000`, `…-sparse-100000` | `B4-http-ops-…` (L/P) | 25% |
| `B4-http-ops-query-equivalent-…` (same three) | `B4-http-ops-query-…` | 25% |
| `B4-http-events-equivalent-…` (same three) | `B4-http-events-…` | 25% |

- **Verdicts.** For these five scenario families, the release decision uses
  the equivalent cell's verdict.
- **Frozen cells.** The frozen counterparts are measured and analyzed
  exactly as before. They are reported as descriptive comparisons of the
  additional cost: L/E for import, L/P for the planner families. They carry
  no release verdict.
- Every other B/C cell decides as before.

### 4.2 Why the import reference is equivalent

The candidate keeps the complete registered topology:
- every node and edge, with its `active` and `enabled` flags, validated;
- the effective graph, for connectivity;
- answers to node and edge state;
- later lifecycle operations;
- publication that is atomic with validation.

The frozen reference imported only the effective graph and copied a lean
flag store (vectors). It could not validate the topology, answer
per-entry state, or plan lifecycle operations.

The equivalent reference (`http-lifecycle --scenario import-equivalent`)
does the following in its timed window, per import call:
1. **Capability.** It builds an application catalog of the registered
   topology with flags (`EquivalentStore`: per node, the flag and the
   incident edges with their flags). That is the structure the ops planner
   uses, so it can answer node and edge state and plan later lifecycle
   operations.
2. **Validation.** It applies the lifecycle import's rules:
   - a repeated node or edge with a different flag rejects the import;
   - a self-loop rejects it;
   - identical repeats are accepted once;
   - missing edge endpoints are registered active.

   Graph limits are not configured in these cells, in either arm.
3. **Guarantees.** It derives the effective edges and sends the plain import
   of the effective graph. It adopts the new catalog only when the server
   answers 201, so the application state changes only with a successful
   publication, as the lifecycle server's does.

The request body is serialized untimed in both arms, as frozen. The
equivalence checks (§4.4) run after the windows.

**One change in the candidate arm** of the ops and ops-query equivalent
cells: it keeps its response bodies inside the window (reference-counted
`Bytes`, pushed into a vector reserved before the window) for the
per-operation check. The reference arm keeps its plain responses the same
way.

### 4.3 Why the planner references are equivalent

The plain server alone does not offer lifecycle semantics: the application
planner (frozen, verbatim) keeps the registered topology and flags, and
turns each lifecycle operation into the plain operations that keep the
server's graph equal to the effective graph.

The frozen reference planned untimed, while the candidate does this
bookkeeping inside its window.

In `ops-equivalent`, `ops-query-equivalent` and `events-equivalent`, inside
the timed reference window, for each lifecycle chunk (256 operations, or 128
for events) and right before that chunk's requests, the application does
the following from the planner in its state at the window's start:
1. **Validation and outcome.** For each operation it computes the outcome the
   lifecycle server reports per operation: changed or unchanged, or the
   error code `self_loop`, `unknown_node` or `unknown_edge`. That is part of
   the service offered.
2. **Catalog update.** It updates its registered topology and flags (the
   frozen planner).
3. **Publication.** It sends the plain operations that keep the plain
   server's graph equal to the effective graph. The requests are the frozen
   ones, prebuilt and untimed in both arms.

**Residual limit: atomicity.** A lifecycle batch is one indivisible unit.
When a chunk expands into more than 1,024 plain operations, the frozen
planner splits it into two plain requests. That happens on `hub`: 39
requests against 37 for ops, 76 against 74 for events. Those chunks are then
not atomic on the plain side. The equivalent reference is kept as the frozen
planner sends it; the limit is disclosed, not corrected.

**Server-level evidence only.** D3c's declared fidelity check failed: the
core replay is 24–31% below the server's in-call time. The core-level
attributions of D3b are therefore not part of this argument. The
equivalence rests on the service each arm provides, and on server-level
measurement in this campaign. D3c's PP arm did not compute per-operation
outcomes, so its L/PP figure is not the cost of this reference.

### 4.4 Equivalence checks (after the windows; a failure stops the probe)

The checks run sequentially after both windows of each pair, with no request
in flight. Connectivity agreement alone is not taken as equivalence.
1. **Plan** (all planner families): the plain operations planned in the
   window must equal those the prebuilt requests carried.
2. **Per-operation outcomes** (`ops`, `ops-query`):
   - every outcome the reference computed in its window must equal the
     candidate's per-item result;
   - every `connected` the application forwarded must be answered by the
     plain server as by the candidate;
   - missing kept results are an error.

   The lifecycle feeder (`events`) reports no per-event results, so for
   events the final-state checks are the equivalence check.
3. **Final counts:** the candidate's `/v1/stats` registered nodes and edges,
   active nodes, enabled and effective edges must equal the application
   catalog's.
4. **Registered content.** Every node of the catalog is queried on the
   candidate with `node_state` (same ID and `active` flag). Every registered
   edge is queried with `edge_state` (same endpoints, `enabled` flag and
   effectiveness). With equal counts, the candidate holds nothing else.
5. **Plain server content.**
   - **Nodes:** every node of catalog ∪ removed IDs is checked one by one,
     read-only, with `connected(v, v)`. The node count must equal
     |catalog ∪ removed|.
   - **Edges:** every effective edge is then cut, one by one, through
     `/v1/batch`, or through feeder events in source-managed mode. Afterwards
     the edge count must be 0, having equalled the effective edges before.
   - **Why destructive:** the plain API has no read-only edge query, so the
     edge check mutates this pair's plain server. It does so after the
     windows and the connectivity check; the server is then discarded.
   - **Difference from the lifecycle server, by design:** the plain server
     has no node removal, so removed nodes stay as isolated vertices.
   - **Lease:** the source-managed feeder used for these cuts relies on the
     60 s lease taken when the arm is prepared. A pair, checks included, took
     2–10 s in the smoke runs.

**Before the freeze**, every equivalent cell was smoke-run at its real size,
and injected mutations were each detected (`smoke/README.md`).

## 5. C3

- The C3 rule and window are unchanged: 30 cycles, cycles 1–10 against
  21–30, and the slope.
- The transient (first compaction interval) and the steady state are
  reported from the C cells as before.
- The candidate's catalog tombstone handling, if included (§2.1), is
  measured by the unchanged C cells.

## 6. M_desc and M_reg: probe revision 4

`tools/contention-probe` revision 4 replaces revision 2:
- **ETag refresh:** a bounded `GET /v1/stats` refresh with a 1 s budget (one
  period of the background import cadence), backoff of 10–160 ms, and at
  most 10 attempts. Each read timeout and reconnect is bounded by the
  remaining budget.
- **Connections:** after any refresh I/O error the connection is replaced
  (with a 200 ms floor once the budget is spent). If that also fails it is
  poisoned, so no late reply can be read as the next answer.
- **After a 412:** one retry.
- **Supersedes revision 3** (FREEZE-A4, "for future collections"), which had
  12 attempts and no deadline. Revision 4 has 10 attempts, the 1 s budget and
  the new summary fields. `scripts/tests/test_v070r_amendment4.py` now pins
  revision 4; FREEZE-A4 still pins revision 3's source by hash.
- **Accounting:** `background.imports`. Exhaustion (with its reason), failed
  refreshes and incomplete imports set `import_starved`.

The validity rule is that of the re-qualification, plus amendment 4
(`analyze_v070r_a4.py`): an import configuration without the accounting, or
showing starvation, is INVALID.

## 7. Conformance

The rules are inherited unchanged from re-qualification amendment 3
revision 2 (PROTOCOL §§9–10.7 there):
- the Terminal.app controller, with Claude quit;
- the background class, allowed and recorded;
- interference disclosure only;
- the launcher audit, recorded;
- no soak;
- the launch environment check.

What changes:
- the campaign directory is
  `evidence/v0.7.0-qualification-3-<cand7>-q3-attemptN`;
- the series is **q3**, cap 3, and every directory counts;
- the first conforming attempt is final.

## 8. Analysis and decision

- **Analyzers:** A, R, Rmem and M_reg use the re-qualification analyzers
  unchanged, bound to this matrix. M_desc and M_reg validity use
  `analyze_v070r_a4.py`.
- **B/C:** `analyze_lifecycle_qualification.py` with
  `--expect-equivalent-references`. It then expects the 140-cell matrix and
  requires the collector's `equivalent_references` provenance; without the
  flag nothing changes for earlier runs.
- **Report:** `report_v070q3_bc.py` lists every B/C result: timing, B5 and
  C1–C4. It marks the deciding and descriptive cells (§4.1) and the
  deciding non-PASS results, with C4 EXCEEDS_BUDGET counted as a disclosure
  category.
- **Release decision:** only a CONFORMING attempt whose deciding results are
  all PASS (or IMPROVED, or disclosure categories already defined, such as
  C4 EXCEEDS_BUDGET) supports a release. Every other outcome goes to the
  maintainer.
- **No acceptance with disclosure, no rerun chosen by its result,** and no
  rule changed after collection.

## 9. Sequence

1. The candidate commit is prepared; knotrel tests, Clippy and Rustdoc pass.
2. Tooling is committed and independently reviewed; then `FREEZE.json`.
3. `prepare_campaign.sh CAND FREEZE ATTEMPT q3` builds everything, runs the
   launch-environment check and writes `LAUNCH-COMMAND.txt`.
4. The maintainer runs it in Terminal.app with Claude quit.

## 10. Differences from the re-qualification, in one place

| Area | Re-qualification (FREEZE-A3 rev. 2) | Qualification 3 |
|---|---|---|
| Candidate | e75ff6a | e75ff6a plus the declared product changes (§2.1) |
| B/C cells | 127 | 140: the 13 equivalent cells added (§4.1); frozen cells in a3-3's order, each equivalent cell right after its counterpart (§3) |
| Deciding B4 cells for import, ops, ops-query, events | frozen references (lean store, untimed planner) | capability-equivalent references; frozen cells descriptive |
| Window multipliers | `lifecycle-qualification-v0.5.0/window-multipliers-dcd8ccc.json` | `window-multipliers-q3.json`: the same 61 factors, plus each equivalent cell with its frozen counterpart's factor. The candidate arm is unchanged and the reference arm only slower, so the faster arm's window stays at least 2 ms. |
| `http-lifecycle` | frozen scenarios | `*-equivalent` scenarios added; frozen scenarios unchanged |
| Contention probe | revision 2 | revision 4 (§6); FREEZE-A4's revision 3 superseded |
| M validity rule | frozen supplement rule | plus amendment 4 (`analyze_v070r_a4.py`), installed only by the analysis command |
| Collectors and analyzers | `run_v070r_collect.py`, `analyze_v070r_qualification.py` | `run_v070q3_collect.py` and `analyze_v070q3.py` (the same code, bound to this matrix); B/C analyzer with `--expect-equivalent-references`; `report_v070q3_bc.py` |
| Freeze record | FREEZE-A3.json (plus FREEZE.json, which the recorder requires) | `FREEZE.json` in this directory: the name the R/Rmem/M recorder requires, checked at launch |
| A seeds | 130720–130722; extension 130730–130732 | unchanged (addendum 1, A5) |
| Campaign directory and series | `v0.7.0-requalification-<cand7>-a3-attemptN`, a3, cap 3 | `v0.7.0-qualification-3-<cand7>-q3-attemptN`, q3, cap 3 |
| Thresholds, estimators, pair counts, conformance rules | — | unchanged |

## 11. Phase-3 results that fix §2.1

These are diagnostics, not qualification results
(`results/v0.7.0-requalification/diagnostics/`; plan `DIAGNOSTICS-PLAN-3.md`
with addenda 1–2).

| | Result | Use here |
|---|---|---|
| **D2c** (catalog tombstones) | **T1 meets every criterion.** Detail in D2c's README. | T1 is in the candidate (§2.1) |
| **D3c** (ops fidelity) | **Fidelity not restored.** Core replay 24–31% below the server's in-call time. Server level: L/P +30.1% [+23.1, +36.6]; L/PP −21.3% [−27.2, −14.5] (one ungated run). | Core attributions withdrawn; the equivalence argument is service-based (§4.3) |
| **D4c** (metrics) | **Not resolved:** the decomposition is internally inconsistent (run-level effects are the likely, unshown cause). The declared follow-up was not run, a departure set aside after seeing the data, which **awaits the maintainer's acceptance**. | No metrics change; the `metrics-ops` cell is measured as released, 6% tolerance |
| **D5c** (probe revision 4) | **Verified:** 6/6 imports in all runs; forced runs recover in 22–30 ms. | Revision 4 used (§6) |
| ETag on 412 | Consistent; stale after release, like a stats token. | Not included: no API change |

D2c in detail:
- C3 PASS ×3;
- B5 unchanged;
- peak and steady state −5.1 MiB;
- rebuilds: median 0.7 ms, max 6.5 ms. Same-run compaction maxima were
  22.8–72.3 ms with T1, of which 72.3 is a single outlier; frozen maxima
  were 19.7–27.3 ms;
- B1 fresh-churn ±0.5%, with T1 rebuilding about once per lifecycle window;
- the product reproduces the diagnostic byte for byte, from clean checkouts
  of the candidate and the tooling (D2c `summary-product-clean.txt`);
- ring drift bounded.
