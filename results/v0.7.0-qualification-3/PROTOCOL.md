# knotrel v0.7.0: qualification 3 protocol (draft until FREEZE.json is written)

**Status: revision 3 (§14), frozen when `FREEZE.json` revision 3 is written.**
Revision 2 was frozen at 6afc1f8b (kept as `FREEZE-r2.json`); attempts q3-1
and q3-2 ran under it, both NONCONFORMING, and stay as they are.
Revision 1 was frozen at 66f2f0a9 (kept as `FREEZE-r1.json`). No collection
ran under it. Revision 2 records the maintainer's decisions of 2026-11-20
(§1) and the changes they require (§13). Collection is launched by the
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

**Decisions of 2026-11-20** (before launch, after the revision-1 freeze).
Verbatim:
1. **Hub atomicity:** "correggi la referenza affinché offra la stessa
   atomicità del candidato. Se non è possibile, quelle celle non possono
   essere presentate come equivalenti né qualificare quel requisito."
2. **D4c:** "accetto l'omissione del follow-up come deviazione della sola
   diagnostica. Non considero risolto l'overhead e non concedo deroghe al
   6%: deciderà la misura q3 prevista dal protocollo."
3. **T1:** "mantienilo nel candidato, ma chiarisci se q3 misura e vincola le
   code di latenza delle compattazioni. … Se manca questa copertura, proponi
   prima del nuovo freeze un controllo mirato con criterio motivato."
4. **Ring drift:** "correggi la conclusione: un intervallo della pendenza che
   contiene zero non dimostra crescita limitata."
5. **Disk:** "autorizzo la pulizia degli artefatti di build rigenerabili del
   worktree, preservando binari congelati, evidenze e manifest."
6. "Registra queste decisioni e le modifiche in un nuovo freeze, preservando
   quello precedente, poi rigenera il tentativo e il comando di lancio."

**Decisions of 2026-11-20, second message** (on the revision-2 draft).
Verbatim:
7. **T5:** "Approvo T5 con tolleranza del 25%, come criterio nuovo per le
   pause di compattazione, dichiarato prima della raccolta. Il fatto che sia
   già usato per query_tail non lo rende automaticamente applicabile a
   questa metrica." And: "Prima del freeze precisa aggregazione per coppia,
   intervalli d'incertezza e regole PASS/REGRESSION/INCONCLUSIVE per
   entrambe le metriche. Riporta anche i tempi assoluti; i massimi devono
   essere confrontati su run della stessa durata e workload." (§5.1)
8. **Hub ops/events:** "Mantieni hub ops/`events` descrittivi, senza
   introdurre ora la referenza basata su import sostitutivo. I due requisiti
   restano non qualificati: non possono sparire dal verdetto complessivo né
   consentire di dichiarare qualificazione completa. Questa scelta autorizza
   la raccolta q3, non una riduzione dei requisiti di rilascio." (§4.1, §8)
10. **Revision 3** (after q3-2, 2026-11-20): the maintainer authorized
    fixing the timestamp defect without weakening the check, and "una
    revisione prospettica del protocollo di conformance": an open
    application, an idle Claude, browser or IDE, keyboard input, mouse
    movement and WindowServer activity are no longer violations by
    themselves; interference is detected by measurable indicators, with
    explicit thresholds, windows and hysteresis; one autonomous invocation;
    interference handled without selecting results; "Autorizzo un tentativo
    sostitutivo per il guasto del tooling, oltre al conteggio precedente,
    entro il budget di durata già previsto per una campagna completa. Non è
    un'autorizzazione a ripetere finché i risultati diventano favorevoli."
    (§14)
9. **Smoke wording:** "Correggi anche “13 celle passano tutti i controlli di
   equivalenza”: due non sono equivalenti, pur completando i controlli
   funzionali." (`smoke/README.md`)

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
  - the product reproduces the diagnostic, identical at every checkpoint (net heap and counts).

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

**One experiment is added:** check T5 (compaction pauses, §5.1), with its own
tolerance of 25%. That tolerance is a new criterion, declared before
collection (decision 7); it is not inherited from any existing threshold.

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
  the equivalent cell's verdict, except for the two cells below.
- **Not equivalent (revision 2, decision 1):**
  `B4-http-ops-equivalent-compact-bfs-hub-10000` and
  `B4-http-events-equivalent-compact-bfs-hub-10000`. Their reference cannot
  offer the candidate's atomicity (§4.3). They still run, unchanged and in
  the same position, and are reported as descriptive with no verdict. The
  two requirements they would have qualified (B4 lifecycle batches and
  lifecycle feeder events on `hub` 10k) are **not qualified by this
  campaign**. The report lists them, and their disposition is the
  maintainer's. Eleven equivalent cells decide.
  - No replace-import reference is introduced for `events` (decision 8).
  - The two requirements never disappear from the overall verdict, and
    while they are unqualified this campaign cannot be declared a complete
    qualification, whatever the other results (§8). Running q3 with them
    unqualified authorizes the collection; it does not reduce the release
    requirements.
- **Frozen cells.** The frozen counterparts are measured and analyzed
  exactly as before. They are reported as descriptive comparisons of the
  additional cost: L/E for import, L/P for the planner families. They carry
  no release verdict.
- Every other B/C cell decides as before.
- Each equivalent cell runs immediately after its frozen counterpart (§3).
  That fixed position offset does not affect within-cell paired verdicts.
  Comparisons across the deciding and the descriptive cell of a family carry
  it.

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

**Atomicity (revision 2).** What the candidate guarantees
(`docs/topology-lifecycle.md` §4, `docs/http-api.md`):
- each lifecycle command is one indivisible step: no query sees a node
  partly deactivated or partly removed;
- each request, batch or feeder events, runs under one hold of the graph
  lock, so no query sees a state between its operations.

For the reference to offer the same, each lifecycle chunk must map to one
plain request, and every single command must fit in it. A plain request
carries at most 1,024 operations (`MAX_BATCH_OPERATIONS` in knotrel-server,
for `/v1/batch` and feeder events; not configurable). The plain API has only
`add_node`, `link`, `cut` and `connected`, and the standalone plain server
has no import.

On `hub` 10k this cannot hold. The frozen trace deactivates two hub nodes,
nodes 1754 and 5231. Each deactivation expands into **1,425 and 1,565 plain
cuts**: a single command larger than any plain request. The two chunks that
contain them need two plain requests each (39 requests against 37 for ops,
76 against 74 for events). Changing the chunking cannot fix this: the
indivisible unit is the single command.
- **ops (standalone):** no atomic plain route exists, so the reference cannot
  be corrected.
- **events (source-managed):** the only atomic plain route would be a full
  replacement import (`POST /v1/feeder/import`, mode `replace`) of the
  effective graph for each affected chunk. That is a different reference
  design, with a different cost and generation semantics. It is not adopted
  without a maintainer decision.
- **Consequence (decision 1):** both cells are not equivalent (§4.1).

**Recorded per pair.** In each pair, `http-lifecycle` records:
- `reference_split_chunks`: lifecycle chunks the plain side needed more than
  one request for;
- `reference_max_op_plain_ops`: the largest plain expansion of one command;
- `atomicity_equivalent`.

**Smoke at real size.** Every other planner cell (ops, ops-query and events
on sparse 10k and 100k; ops-query on hub) shows one plain request per chunk
and at most 15 plain operations per command (`smoke/smoke-r2-draft.txt`). If a deciding cell nevertheless
records `atomicity_equivalent: false`, the report marks it `NOT_EQUIVALENT`
among the deciding non-PASS results (§8). This is fail-closed.

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

### 5.1 Compaction latency tails: check T5 (decisions 3 and 7)

**Without T5, q3 would not measure or constrain the latency tails of engine
compactions or catalog rebuilds:**
- the C cells measure memory and logical counts only (C1–C4);
- B1–B4 decide on median window times.
  - A B1 fresh-churn window contains about one catalog rebuild and one engine
    compaction at 10k (three at 1k), from D2c's event counts
    (`raw/b1-events/`).
  - But those pauses are on graphs of 1k and 10k nodes, where a compaction
    is short, and they enter only a window total judged by its median over
    24 pairs. No B cell times a single pause, and none runs lifecycle churn
    at 100k, where D2c measured compactions of 11–16 ms (median);
- M_reg measures HTTP client latency without lifecycle churn.

D2c's T1 timing runs showed higher compaction tails: ring p99 31.1 against
17.3 ms, hub maximum 72.3 against 27.3 ms, each from one run on an ungated
laptop. The maintainer approved the targeted check proposed in
`PROPOSAL-T1-TAILS.md` (decision 7). It is specified here; where this
section and the proposal differ, this section rules.

**Question.** Does T1 lengthen the longest pauses of lifecycle calls under
fresh-ID churn at 100k nodes? A pause is the time of one lifecycle call,
including any engine compaction or catalog rebuild it triggers.

**Arms.**
- **B:** `core-lifecycle`, timing build, frozen probe source, built against
  knotrel `e75ff6a` (the a3-3 candidate, without T1) into
  `targets/t1base-probes`.
- **C:** the same source built against the candidate `fa5f3a9` (with T1):
  the `cand-probes` binary of the B/C cells.
- T1 is the only executed-code difference between the two sources (§2.1:
  `git diff e75ff6a fa5f3a9` touches `crates/knotrel-core/src/topology.rs`
  and documentation only; the lockfile is the same), so the comparison
  isolates T1.

**Workload: the same duration and the same work in every run.**
- `core-lifecycle pauses`: the frozen C workload, fresh-ID churn of 5% per
  cycle on 100,000 nodes, seed 5000001, `compact-bfs`, on `sparse`, `ring`
  and `hub`. Each run is **600 cycles** from a fresh process: 15,000,000
  lifecycle calls on `sparse` and `hub` (25,000 per cycle), 12,000,000 on
  `ring` (20,000 per cycle). Construction is not timed.
- Every call is timed separately with `Instant`, identically in both arms.
  After each cycle, outside the timing, the probe checks the logical counts
  against the independent model (a difference stops the run) and reads
  the storage statistics; a drop of `retired_vertices` marks the cycle of a
  compaction. Reading them walks the catalog (O(n)) between cycles. That is
  identical in both arms, but it changes cache state before the next
  cycle's first calls.
- The raw file is self-describing: build, `pauses_start` (engine,
  topology and workload), 600 cycle records, `pauses_end`, and nothing
  else.
- **Equality is checked, not assumed.** Within a topology, the analysis
  requires every run of both arms, warmup included, to have the same
  schedule digest, result digest, calls per cycle, final logical counts and
  compaction cycles. So maxima are always compared over the same number of
  calls on the same sequence of operations. Otherwise the analysis is
  invalid.
- **Thirty compactions.** The pre-freeze smoke (both arms, all three
  topologies; `smoke/t5-smoke.txt`) compacts at cycles 20, 40, …, 600. The analysis requires exactly 30 compaction cycles,
  the last at cycle 600, so the 30 intervals cover every cycle; otherwise it
  is invalid.

**Metrics per run.**
- **P_max:** the longest single call of the run.
- **P_90:** interval k is the cycles after compaction k−1, up to and
  including compaction k. Its maximum is its longest call. P_90 is the 27th
  of the 30 interval maxima sorted in ascending order, the typical bad
  compaction pause.

**Design.**
- 2 warmup pairs, then 12 analyzed pairs per topology; a pair is two
  consecutive runs, one per arm.
- Warmup pair −2 runs C first, pair −1 B first. The first arm of the 12
  analyzed pairs is a 6/6 shuffle by `random.Random(f"50730:{topology}")`.
- Runs are interleaved by round: round r runs pair r of each topology, the
  topologies in an order shuffled by `random.Random(f"50730:round:{r}")`.
- 84 runs of 7–12 s plus construction, about 17 minutes, in the chain
  after B/C
  (`scripts/run_v070q3_t5.py`, every run gated, label `T5:`). A failed run
  stops the collector and the chain: FAILED, no verdict.

**Aggregation, interval and rule (both metrics; frozen before collection).**
- Per pair: d = ln(C / B), the metric of the C run over that of the B run
  of the same pair.
- Over the 12 analyzed pairs, sorted: the interval is [d(3), d(10)]. It is
  a distribution-free interval for the median of d, coverage 1 − 2 ·
  P(Bin(12, ½) ≤ 2) = 96.1%. The point estimate is the median of d.
- Tolerance t = 25%:
  - **PASS** if d(10) ≤ ln(1.25);
  - **REGRESSION** if d(3) > ln(1.25);
  - **INCONCLUSIVE** otherwise.
- The rule applies to P_max and P_90 on each topology: **six deciding
  results**. `scripts/analyze_v070q3_t5.py` computes them with
  `summarize_metric` of `analyze_bc_qualification.py`, reused unchanged.
- Any non-PASS, and an invalid analysis, goes to the maintainer as every
  other deciding non-PASS does. There is no waiver and no extension. An
  invalid analysis writes a marker that the report turns into six INVALID
  deciding rows, so B/C can still be reported.

**Absolute values, reported with every result:** per arm, the median,
minimum and maximum of P_max and P_90 in ms; per run, the wall and timed
duration and the mean call time; the 12 pairs' values; the kind of the
longest call in the compaction cycles.

**Known limits, disclosed before collection.**
- **P_max is one extreme** over 12–15 million calls. Preemption or a move
  between core types during a 15–25 ms compaction can inflate one run. The
  balanced order spreads that over both arms. The [d(3), d(10)] interval
  absorbs at most two such pairs on each side; more can make a result
  INCONCLUSIVE. P_90 is less exposed.
- **`hub` is a hub only at first.** With uniform 5% churn the original hub
  nodes are removed within the first tens of cycles (survival 0.95^c), and
  D2c's interval maxima for `hub` and `sparse` coincide after about 50
  intervals. Most `hub` intervals of T5 therefore measure a graph without
  its hub; the topology mainly changes the first intervals.

**Why 25% is the T5 criterion.** No product document states a pause
objective, so an absolute ceiling would be chosen without a basis. A
relative bound answers the question asked, T1's effect. 25% is the
maintainer's decision for this metric (decision 7); it equals the
`query_tail` tolerance by choice, not by inheritance.

### 5.2 Ring drift (decision 4)

D2c's "bounded" classification of the ring drift is withdrawn (D2c README,
"Ring drift: observed behaviour"; plan addendum 4):
- **Observed:** a rise of about 90 KiB over the first ~50 compaction
  intervals, then a 48 KiB band up to cycle 6,000.
- **Bounded by construction:** the catalog table (under T1) and the engine
  (rebuilt at every compaction).
- **Not bounded by construction:** the per-node incident capacity. It is
  released at node removal, but its level depends on the workload's degree
  process.

C3 itself is unchanged and decides on 30 cycles as before.

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

**The attempt prepared under revision 1.** `…-q3-attempt1` was prepared
from freeze 66f2f0a9 and **never launched**: it has no `logs/CONFORMANCE.txt`,
no measurement and no result.
- **Renaming.** Following the precedent of the unlaunched soak directories
  of the re-qualification (`…-a2-soak2.unlaunched-<freeze>`), it is renamed
  `…-q3-attempt1.unlaunched-66f2f0a9`. Its revision-1 launch command can then
  no longer run.
- **Kept:** sources, logs, manifests, binary hashes and every release
  binary listed in `binaries-sha256.txt`.
- **Removed:** only the regenerable intermediate build files (decision 5).
- **Count.** It used no attempt: the series budget counts launched
  attempts, and no result exists that could be chosen. The attempt prepared
  under revision 2 is therefore q3-1 again. This is decision 6
  ("rigenera il tentativo"); it is recorded, not inferred.

## 8. Analysis and decision

- **Analyzers:** A, R, Rmem and M_reg use the re-qualification analyzers
  unchanged, bound to this matrix. M_desc and M_reg validity use
  `analyze_v070r_a4.py`.
- **B/C:** `analyze_lifecycle_qualification.py` with
  `--expect-equivalent-references`. It then expects the 140-cell matrix and
  requires the collector's `equivalent_references` provenance; without the
  flag nothing changes for earlier runs.
- **T5:** `analyze_v070q3_t5.py T5 --expect-base-rev e75ff6a… --expect-cand-rev
  fa5f3a9… --expect-probes-rev <freeze commit>` (§5.1).
- **Report:** `report_v070q3_bc.py BC-analysis.json T5-analysis.json` lists
  every B/C result (timing, B5 and C1–C4) and the six T5 results. It marks:
  - the deciding, descriptive and not-equivalent cells (§4.1);
  - the deciding non-PASS results, with C4 EXCEEDS_BUDGET counted as a
    disclosure category and `NOT_EQUIVALENT` as non-PASS (§4.3);
  - the unqualified requirements, always, and `qualification_scope`: not
    complete while any requirement is unqualified;
  - any not-equivalent cell whose records nevertheless show equivalence, as
    an inconsistency.
- **Release decision:** only a CONFORMING attempt whose deciding results are
  all PASS (or IMPROVED, or disclosure categories already defined, such as
  C4 EXCEEDS_BUDGET), T5 included, **and with no unqualified requirement**
  supports a release. The report's `overall.release_supported_by_q3` is
  false while any requirement is unqualified. Every other outcome goes to
  the maintainer.
- **Unqualified requirements (§4.1)** receive no verdict from this campaign.
  They are not PASS, and their disposition is the maintainer's. They stay in
  the overall verdict. While any is unqualified, no outcome makes q3 a
  complete qualification (decision 8), and q3 alone does not support the
  release of the requirements they cover.
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
| Deciding B4 cells for import, ops, ops-query, events | frozen references (lean store, untimed planner) | capability-equivalent references; frozen cells descriptive; hub ops and hub events equivalent cells not equivalent (revision 2, §4.3), so those two requirements are unqualified |
| Window multipliers | `lifecycle-qualification-v0.5.0/window-multipliers-dcd8ccc.json` | `window-multipliers-q3.json`: the same 61 factors, plus each equivalent cell with its frozen counterpart's factor. The candidate arm differs only by keeping its response bodies (§4.2, a reference-count push per request), and the reference arm is only slower, so the faster arm's window stays at least 2 ms. |
| `http-lifecycle` | frozen scenarios | `*-equivalent` scenarios added; frozen scenarios unchanged |
| Contention probe | revision 2 | revision 4 (§6); FREEZE-A4's revision 3 superseded |
| M validity rule | frozen supplement rule | plus amendment 4 (`analyze_v070r_a4.py`), installed only by the analysis command |
| Collectors and analyzers | `run_v070r_collect.py`, `analyze_v070r_qualification.py` | `run_v070q3_collect.py` and `analyze_v070q3.py` (the same code, bound to this matrix); B/C analyzer with `--expect-equivalent-references`; `report_v070q3_bc.py` |
| Freeze record | FREEZE-A3.json (plus FREEZE.json, which the recorder requires) | `FREEZE.json` in this directory: the name the R/Rmem/M recorder requires, checked at launch |
| A seeds | 130720–130722; extension 130730–130732 | unchanged (addendum 1, A5) |
| Campaign directory and series | `v0.7.0-requalification-<cand7>-a3-attemptN`, a3, cap 3 | `v0.7.0-qualification-3-<cand7>-q3-attemptN`, q3, cap 3 |
| T5 (compaction pauses) | — | added (§5.1): B = probes on e75ff6a, C = candidate probes; P_max and P_90, 12 pairs, tolerance 25% (a new criterion, decision 7); runs after B/C |
| Thresholds, estimators, pair counts, conformance rules | — | unchanged for every existing experiment |
| Freeze | — | revision 2 (`FREEZE.json`); revision 1 kept as `FREEZE-r1.json` (66f2f0a9) |

## 11. Phase-3 results that fix §2.1

These are diagnostics, not qualification results
(`results/v0.7.0-requalification/diagnostics/`; plan `DIAGNOSTICS-PLAN-3.md`
with addenda 1–2).

| | Result | Use here |
|---|---|---|
| **D2c** (catalog tombstones) | **T1 meets every criterion.** Detail in D2c's README. | T1 is in the candidate (§2.1) |
| **D3c** (ops fidelity) | **Fidelity not restored.** Core replay 24–31% below the server's in-call time. Server level: L/P +30.1% [+23.1, +36.6]; L/PP −21.3% [−27.2, −14.5] (one ungated run). | Core attributions withdrawn; the equivalence argument is service-based (§4.3) |
| **D4c** (metrics) | **Not resolved:** the decomposition is internally inconsistent (run-level effects are the likely, unshown cause). The declared follow-up was not run; the maintainer **accepted this as a departure of the diagnostic only** (2026-11-20). The overhead is not resolved and the 6% budget has no exception. | No metrics change; the `metrics-ops` cell is measured as released and decides at 6% |
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
- the product reproduces the diagnostic, identical at every checkpoint (net heap and counts), from clean checkouts
  of the candidate and the tooling (D2c `summary-product-clean.txt`);
- ring drift: about 90 KiB over the first ~50 intervals, then a 48 KiB band
  to cycle 6,000; bounded growth **not** demonstrated (§5.2);
- compaction tails: not covered by the existing experiments; measured by
  check T5 (§5.1).

## 12. Reviews before the freeze

1. **Independent review of `c9ae8cc6..1e71d6c0` and knotrel `f34af87d`.** It
   found four blockers:
   - the recorder needs `FREEZE.json`;
   - the B/C analyzer expected 127 cells;
   - the frozen B/C order changed;
   - free disk space.

   It also found seven should-fix items and minors. All were addressed
   (`7dd1fdb7`, `840ab95d`, `19ce66d3`, `704b2595`; knotrel `fa5f3a9`), except:
   - disk space, an environment item: about 5.6 GiB is free;
   - the D4c follow-up, which awaits the maintainer's acceptance.
2. **Delta review of `1e71d6c0..704b2595` and knotrel `fa5f3a9`.**
   - Every earlier finding resolved, except disk space (environment) and the
     D4c acceptance, which is recorded as pending.
   - No new blocker or should-fix item.
   - Five minors, addressed before the freeze: §4.1 and §10 wording, the
     probe's reconnection of a poisoned connection before the next import,
     the usage line, and "identical at every checkpoint" in place of "byte
     for byte".

3. **Independent review of revision 2, `66f2f0a9..56ab1b27`.** No blocker.
   Five should-fix items, all addressed:
   - the report now refuses a planner equivalent cell without an atomicity
     record, and the B/C analyzer marks it invalid (it failed open before);
   - the report reads `unqualified_requirements` strictly, requires at
     least one per not-equivalent cell, and gives an `overall` verdict that
     never supports a release while any is unqualified; §8 says so;
   - the T5 smoke is committed (`smoke/t5-smoke.txt`);
   - the freeze lists the T5 scripts and `cli_paths.py`; revision 1 is kept
     as `FREEZE-r1.json`;
   - the T5 analyzer turns every failure into "T5 INVALID" and a marker,
     and the report gives six INVALID rows for it.

   Minors addressed: per-topology call counts and duration; "longest call in
   the compaction cycles" in place of "call that compacted"; the report
   checks the six T5 ids; the raw file is self-describing and trailing
   records are rejected; the catalog walk between cycles, the exposure of
   P_max to single extremes, and the dissolving hub are disclosed (§5.1).
   Not changed: the informational `__TEXT` comparison does not include the
   e75ff6a probe (its source differs by construction).

## 13. Revision 2 (2026-11-20)

What changed since the revision-1 freeze (66f2f0a9), from the decisions in
§1. Nothing else changed: the existing experiments' seeds, workloads, run
order, estimators, thresholds and conformance rules are the same. T5 is the
one added experiment (§5.1).

| Decision | Change |
|---|---|
| 1, hub atomicity | Probe records atomicity per pair. Hub ops and events equivalent cells are moved to `not_equivalent` in the matrix, and their requirements are listed as unqualified. Analyzer copies the atomicity fields; the report is fail-closed (§4.1, §4.3, §8). |
| 2, D4c | Departure accepted for the diagnostic only; no exception to 6% (§11; plan addendum 4) |
| 3 and 7, T1 tails | Coverage without T5 stated as absent; T5 approved with a 25% tolerance as a new criterion and specified in full (§5.1): `core-lifecycle pauses`, the e75ff6a probe build, `run_v070q3_t5.py`, `analyze_v070q3_t5.py`, T5 rows in the report, the chain step, the gate count `T5` |
| 4, ring drift | Classification withdrawn; observed behaviour and structural bounds reported (§5.2; D2c README) |
| 5, disk | The knotrel worktree's build cache (8.4 GiB) removed; regenerable intermediates of the unlaunched attempt removed, its binaries kept (§7) |
| 8, hub ops/events | Kept descriptive, no replace-import reference; requirements stay in the verdict; `qualification_scope` in the report (§4.1, §8) |
| 9, smoke wording | `smoke/README.md` corrected: the two hub cells complete the functional checks but are not equivalent |
| 6, freeze | Revision 1 kept as `FREEZE-r1.json`; `FREEZE.json` revision 2 written after review; the unlaunched attempt renamed, and q3-1 prepared anew (§7) |

## 14. Revision 3 (2026-11-20, decision 10)

Two distinct changes: a **technical fix** (§14.1), which corrects a defect
and changes no rule, and a **protocol change** (§14.2–14.6), which replaces
the conformance policy for attempts prepared under revision 3. Attempts
q3-1 and q3-2 are kept unchanged and NONCONFORMING; nothing here relabels
them.

### 14.1 Technical fix: heartbeat timestamps

- **Defect.** The monitor wrote each heartbeat's time to its log rounded to
  the millisecond, and the exact time to its status file. The gate waited on
  the status file for a heartbeat after a child's end, then looked for it in
  the log. In q3-2 the heartbeat came 0.14 ms after the end of child 610: the
  exact time was after the end and the rounded one before it, so the gate
  stopped the attempt for a heartbeat that existed.
- **Fix.** `conformance_monitor.sample_line` writes the time exactly (JSON
  round-trips a float), the same value the status file carries. Both sides
  compare values of the same clock and representation; no tolerance is added.
  The new monitor (§14.3) does the same.
- **Tests** (`scripts/tests/test_v070q3_r3.py`, `TimestampDefect`): the q3-2
  values reproduce the false stop with the old writer; with the fix the same
  values pass; heartbeats before, at and after the end; real gaps, a dead
  monitor and an incomplete log line are still detected. The regression
  tests fail when run against the old writer.
- No probability is attached to the defect: one occurrence in 610 children
  (q3-2) and none in 926 (a3-3) is too little to estimate one.

### 14.2 Protocol change: presence is context, interference is measured

From revision 3 the rule "nothing outside the allow-list runs and no user
input occurs" no longer applies. Instead:
- applications, Claude (including the session that started the runner),
  browsers, IDEs, keyboard and mouse input and WindowServer activity are
  **recorded as context** and never stop or invalidate anything by
  themselves;
- **interference** is what the indicators of §14.3 measure. A build,
  indexing or local inference that uses enough CPU makes the runner wait; the
  application that might start one is not forbidden;
- the frozen collectors' presence checks are disabled under this policy:
  `check_no_builds` (R, Rmem, M) and A's `competing_workloads`. Their AC
  power and thermal checks stay;
- no launcher is quiesced and no application is closed, parked or killed.
  The runner changes no system or IDE setting; its only temporary measure is
  a `caffeinate -dimsu -w <runner>` assertion that ends with the runner.

### 14.3 Indicators, thresholds and their basis

The monitor (`scripts/interference_monitor.py`) samples once per second.
The campaign (the runner and all its descendants: collectors, benchmarks,
servers, the monitor) is excluded from the external load.

| Indicator | How it is measured | Rule |
|---|---|---|
| External CPU | cumulative CPU time of every process outside the campaign tree, per second (`ps`) | **wait** before a unit while the 30-s mean exceeds 0.6 cores or the 10-s mean exceeds 1.5; **invalidate** a unit if any 10-s mean inside it exceeds 1.5 |
| Memory pressure | `kern.memorystatus_vm_pressure_level` | wait / invalidate above level 1 (normal) |
| Sleep | growth of (wall clock − monotonic clock), which stops during sleep | invalidate on a jump above 2 s; wait 30 s after one |
| Power | `pmset -g batt`, every sample | battery: wait / invalidate |
| Thermal | `pmset -g therm`, every sample | any recorded thermal or performance warning, or a CPU speed limit below 100: wait / invalidate |
| Monitor coverage | sample gaps; monitor status | from the last sample at or before a unit's start to the first at or after its end, a gap above 2.5 s, or a missing end sample: invalidate; monitor gone, or no new sample for 30 s of monotonic time (sleep excluded): stop (MONITOR LOST) |

**Basis of the CPU thresholds** (host observations only; no B/C, T5 or
other measured result was consulted):
- The two collections with the strictest host state so far, a3-3 and q3-2,
  ran with Claude quit and nobody at the Mac. Their monitor logs record each
  second the five busiest non-campaign processes. Summed, the 10-s mean
  reached at most 1.08 and 1.07 cores, and the 30-s mean at most 0.58 and
  0.56 cores. Those peaks come from system daemons (`deleted`, `cloudd`,
  `triald_system`, `fseventsd`), the background that the earlier protocol
  accepted.
- **1.5 cores (10 s)** is therefore above everything a quiet host produced,
  so ordinary background never invalidates a unit. On this Mac (Apple M3,
  four performance and four efficiency cores) it means sustained external
  work of more than one and a half cores: builds, indexing and local inference
  typically use several cores.
- **0.6 cores (30 s)** is just above the quiet hosts' 30-s maximum, so a
  quiet host is always ready, and well below 1.5, which gives hysteresis: a
  unit does not start right after a load until the load has clearly ended.
- The windows follow the sample rate: 10 s smooths single-sample spikes (a
  2-s burst of 4 cores raises a 10-s mean by 0.8); 30 s is a short settle
  interval that a quiet host passes at once.
- The new monitor's per-process sum covers all processes, not only the top
  five, so it reads somewhat higher than the old logs on the same host. The
  live smoke (`smoke/r3-monitor-smoke.txt`) records its idle level with this
  session active.

**Memory, power, thermal and sleep** use the operating system's own states,
so they need no chosen number. The 2-s sleep jump is twice the sample
interval. **Disk activity is not measured:** it cannot be attributed to
processes without elevated privileges, and the campaign does its own I/O.
Heavy indexing and builds show up as external CPU. **Not seen:** an external
process that starts and exits between two samples.

### 14.4 Units, recovery and budget (declared before collection)

- **Wait** happens only before a unit, never inside one; no timed process is
  suspended or resumed.
- **Judgement** waits for the first sample at or after the unit's end; that
  sample's process table is read after its time, so its CPU delta covers the
  unit to its end. Every sample carries the power and thermal readings, so a
  short unit is never judged without one.
- **Unit = what must be judged together:**
  - B/C: the cell (one child that runs both arms, the warmup and the 12 pairs);
  - T5, R, M_reg: the pair, both arms;
  - Rmem: the cell (`ref` and `cand`);
  - M_desc: the child (one server's configuration list; unpaired);
  - A: the whole block (A main, A extension). Its frozen collector cannot
    repeat one pair; the gate waits before each child and an invalid child
    invalidates the block.
- **Repetition:** an invalid unit is repeated **whole**, at most 2 times (3
  attempts); an invalid A block is restarted at most once. A unit still
  invalid after that ends the campaign as RECOVERY EXHAUSTED: no result is
  produced from it, so it stays inconclusive.
- **Validity depends only on telemetry** and these rules, never on a
  measured value, a verdict or a distance to a threshold.
- **Everything is kept:** invalid attempts with their reasons and intervals
  (`gate/units.jsonl`), their outputs (`BC/invalidated/`,
  `T5/raw/invalidated/` and `T5/invalidated.jsonl`, the run logs' `invalidated`
  lists and `raw/invalidated/` for R, Rmem, M, `invalidated/` for A blocks),
  and every wait with its reasons.
- **Limits:**
  - one wait longer than 10 min ends the campaign as BLOCKED ("blocked by
    sustained host load");
  - the whole attempt has **105 minutes** from its start, waits and
    repetitions included. This is the upper end of the duration stated for a
    complete campaign (1 h 30–1 h 45). q3-2's steps took 82 minutes; judging
    each of about 730 units adds the wait for the next sample, 0.66–0.93 s
    in the live smoke (about 8–9 minutes in all); about 13 minutes remain
    for waits and repetitions.
    The budget starts after the preflight. Past the deadline no new unit
    starts: BUDGET EXHAUSTED.
  - A's frozen collector keeps its own 45-minute deadline per block; waits
    inside A count against it, and exceeding it is FAILED.
  - The frozen AC and thermal checks of A (per session) and of R, Rmem and
    M (per child) still stop their collector (FAILED) if power or thermal
    state is bad at that moment; the gate normally waits before that point.

  Each of these ends with everything preserved, and is reported to the
  maintainer.

### 14.5 The runner

`scripts/run_v070q3_autonomous.py CAMP CAND` (the prepared
`LAUNCH-COMMAND.txt`), one invocation:
1. preflight, which measures nothing: frozen files and binaries match their
   hashes, AC power, disk space, no unrestored quiesce from earlier attempts,
   no output yet. A refusal is NOT STARTED, writes no `CONFORMANCE.txt` and
   uses no attempt;
2. starts `caffeinate` and the monitor, and requires 6 gap-free samples,
   including a power/thermal sample, within 20 s;
3. runs A main, A analysis, A extension if required, B/C, T5, R, Rmem,
   M_desc and M_reg, with the frozen collectors' arguments (a test compares
   them with the frozen chain). Each collector waits by itself before each
   unit;
4. end checks: every collector child has exactly one valid unit record
   (final blocks only), and binaries are unchanged;
5. always, including after an error or a signal: stops the current child,
   the monitor and `caffeinate`; writes `logs/CONFORMANCE.txt`,
   `SUMMARY.json`, `SUMMARY.txt` (status, cause, invalidated units, waits,
   steps) and output checksums; checks that no earlier quiesce is left
   unrestored.

Statuses: CONFORMING (all units valid under these rules), BLOCKED, BUDGET
EXHAUSTED, RECOVERY EXHAUSTED, MONITOR LOST, FAILED, INTERRUPTED, NOT
STARTED. Only CONFORMING attempts give verdicts. The agent that starts the
runner does no other work while it runs.

### 14.6 Review before the freeze

Independent review of `85485c3e`: one probable blocker and eight should-fix
items, all addressed before the freeze:
- **blocker:** waiting for a sample one second after each unit cost about
  2 s per unit (about 23 minutes in all) and would have exhausted the
  budget. Now the first sample at or after the end is used (§14.4);
- gaps straddling a unit's start or end are detected;
- power and thermal state are read in every sample;
- monitor silence is measured on monotonic time and waited for up to 30 s,
  so a sleep or a short stall does not end the campaign;
- any preflight failure is NOT STARTED, and a monitor that fails to start
  leaves the directory relaunchable;
- `CONFORMANCE.txt` is written before anything else at the end, and partial
  record lines are skipped;
- the launch command detaches the runner into its own session;
- B/C cells are keyed by binary and arguments (core and core-count cells
  share arguments);
- the collector runs in its own process group, which the runner stops whole.

Minors addressed: stop reasons are recorded before a gate exit; reasons are
de-duplicated without merging distinct kinds; every monitor command has a
10-s timeout; T5 keeps a failing run's output; the budget starts after the
preflight. Not changed (disclosed in §14.4): A's own 45-minute deadline and
the frozen collectors' AC and thermal checks. Residual test gap: the A and
B/C adapters are tested with fakes, not end to end through the frozen
collectors.

### 14.7 What does not change

Candidate, reference, experiments, cells, seeds, run order, estimators,
thresholds, the T5 specification, the equivalence rules, the unqualified
requirements and the release rule of §8 are unchanged. The first CONFORMING
attempt is final.

### 14.8 The replacement attempt

q3-2 failed on the tooling defect of §14.1. Under decision 10 its
replacement is **q3-3**, prepared from the revision-3 freeze (`attempts_cap`
4 in the matrix for this reason only). It is one attempt, not permission to
repeat until results are favourable.

