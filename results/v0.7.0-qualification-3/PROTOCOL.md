# knotrel v0.7.0: qualification 3 protocol (draft until FREEZE-Q3.json is written)

**Status: DRAFT.** This protocol is frozen by `FREEZE-Q3.json` after its
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
- **Candidate:** knotrel 0.7.0 at the commit recorded in `FREEZE-Q3.json`.
  It is e75ff6a plus the product changes that met their declared criteria
  in `DIAGNOSTICS-PLAN-3.md` (§2.1), and nothing else.

### 2.1 Product changes in the candidate

*(Completed from D2c and D4c before the freeze; see §11.)*

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
everything anew. The cell order is the same, which keeps the comparison with
a3-3 direct.

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
does the following in its window, per import call:
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

The request body is serialized untimed in both arms, as frozen. After the
window, the probe checks:
- that the catalog's effective edges equal those imported;
- the catalog's node, registered-edge and active-node counts;
- that connectivity answers agree between the arms.

### 4.3 Why the planner references are equivalent

The plain server alone does not offer lifecycle semantics: the application
planner (frozen, verbatim) keeps the registered topology and flags, and
turns each lifecycle operation into the plain operations that keep the
server's graph equal to the effective graph.

The frozen reference planned untimed. D3b showed that the candidate does
this bookkeeping inside its window. D3c measured both on one binary.

In `ops-equivalent`, `ops-query-equivalent` and `events-equivalent`:
- the planner, in its state at the start of the window, plans each
  lifecycle chunk (256 operations, or 128 for events) inside the reference
  window, right before that chunk's requests;
- the requests are the frozen ones, prebuilt and untimed in both arms;
- connectivity answers are checked between the arms after the window, as
  before.

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
- **After a 412:** one retry.
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

- **Analyzers:** A, B/C, R, Rmem and M_reg use the re-qualification
  analyzers unchanged, bound to this matrix. M_desc and M_reg validity use
  `analyze_v070r_a4.py`.
- **Report:** a summary lists, per family, the deciding cells and the
  descriptive cells (§4.1).
- **Release decision:** only a CONFORMING attempt whose deciding results are
  all PASS (or IMPROVED, or disclosure categories already defined, such as
  C4 EXCEEDS_BUDGET) supports a release. Every other outcome goes to the
  maintainer.
- **No acceptance with disclosure, no rerun chosen by its result,** and no
  rule changed after collection.

## 9. Sequence

1. The candidate commit is prepared; knotrel tests, Clippy and Rustdoc pass.
2. Tooling is committed and independently reviewed; then `FREEZE-Q3.json`.
3. `prepare_campaign.sh CAND FREEZE ATTEMPT q3` builds everything, runs the
   launch-environment check and writes `LAUNCH-COMMAND.txt`.
4. The maintainer runs it in Terminal.app with Claude quit.

## 10. Differences from the re-qualification, in one place

| Area | Re-qualification (FREEZE-A3 rev. 2) | Qualification 3 |
|---|---|---|
| Candidate | e75ff6a | e75ff6a plus the declared product changes (§2.1) |
| B/C cells | 127 | 140: the 13 equivalent cells added (§4.1) |
| Deciding B4 cells for import, ops, ops-query, events | frozen references (lean store, untimed planner) | capability-equivalent references; frozen cells descriptive |
| Window multipliers | `lifecycle-qualification-v0.5.0/window-multipliers-dcd8ccc.json` | `window-multipliers-q3.json`: the same 61 factors, plus each equivalent cell with its frozen counterpart's factor. The candidate arm is unchanged and the reference arm only slower, so the faster arm's window stays at least 2 ms. |
| `http-lifecycle` | frozen scenarios | `*-equivalent` scenarios added; frozen scenarios unchanged |
| Contention probe | revision 2 | revision 4 (§6) |
| M validity rule | frozen supplement rule | plus amendment 4 (`analyze_v070r_a4.py`), installed only by the analysis command |
| Collectors and analyzers | `run_v070r_collect.py`, `analyze_v070r_qualification.py` | `run_v070q3_collect.py` and `analyze_v070q3.py`: the same code, bound to this matrix |
| A seeds | 130720–130722; extension 130730–130732 | unchanged (addendum 1, A5) |
| Campaign directory and series | `v0.7.0-requalification-<cand7>-a3-attemptN`, a3, cap 3 | `v0.7.0-qualification-3-<cand7>-q3-attemptN`, q3, cap 3 |
| Thresholds, estimators, pair counts, conformance rules | — | unchanged |

## 11. Phase-3 results that fix §2.1

*(Completed before the freeze.)*
