# D1 — B4 `import-high` REGRESSION: cost breakdown and capability-equivalent comparison

Diagnostic ordered on 2026-11-19 (DIAGNOSTICS-PLAN.md, D1). It is not part
of the qualification. The a3-3 verdict, REGRESSION +413.26% [+375.24,
+446.79] against a 100% tolerance, stands, and no threshold changes.

**Setup.** The harness is in `harness/`. It builds against the a3-3
candidate checkout and lifecycle-probes library; the binary is in
`raw/binary-sha256.txt`.
- The topology, flags and bodies match the frozen
  `http-lifecycle --scenario import`: sparse, 10,000 nodes, seed 5000001,
  60% inactive, 30% disabled.
- Each import goes to a fresh source-managed server in process.
- 12 pairs after 2 warmup pairs. All three arms run in every pair, in a
  rotating order.
- One run, on the developer laptop with normal background activity.

## Arms

| Arm | Server | Body | Graph held |
|---|---|---|---|
| L | lifecycle | full registered topology with flags | 10,000 nodes; catalog of 19,991 registered edges with flags; engine over the 2,139 effective edges |
| F | plain | full registered topology, everything active | the same nodes; an engine over all 19,991 edges, no flags |
| E | plain | effective graph only, plus the application flag store (the B4 reference) | 10,000 nodes, 2,139 effective edges |

F parses the same registered volume but does not hold the same data
structures as L, so it does not isolate flags at equal volume. The lifecycle
server keeps every registered entry in its catalog and builds its
connectivity engine from the effective edges only (2,139 here). F builds a
plain engine over all 19,991 edges. F also cannot answer the effective-graph
connectivity that L answers, so it is not a drop-in alternative.

## Results (`raw/d1.jsonl`)

| | L | F | E |
|---|---|---|---|
| Median import time (incl. E's flag store) | 2.335 ms | 2.006 ms | 0.467 ms |
| Body bytes | 985,340 | 744,252 | 141,320 |
| Parse-only proxy (`sonic_rs::Value`, median of 25) | 0.578 ms | 0.351 ms | 0.086 ms |
| Server `prepare` phase (one metrics-enabled import) | 2.172 ms | 1.845 ms | 0.313 ms |
| Server `publish` phase | 0.018 ms | 0.014 ms | 0.009 ms |

Paired ratios over the 12 pairs (median, min–max):

| Ratio | Median | Range (pair min–max) | Meaning |
|---|---|---|---|
| L / E | 4.96 | 4.18–5.71 | the B4 comparison (+396%; a3-3 measured +413%) |
| F / E | 4.42 | 3.71–4.92 | parsing and building a plain engine over 9.3× more edges |
| L / F | 1.137 | 1.078–1.215 | lifecycle import against a plain import of the same volume (different structures; see above) |

## Breakdown

- **Volume.** A plain server given the full registered volume (F) costs
  4.42× the reference. The share of L's excess over E that F also shows
  depends on the method: 86% (median of paired ratios, 3.42 / 3.96), 82%
  (differences of median times) or 93% (log ratios). F's body is 5.3× E's,
  and its server `prepare` phase (parse and build) is 5.9× longer.
- **L against F** (+13.7%, pair range 7.8–21.5%): L's body is 32% larger
  (the node objects `{"node":…,"active":false}` and the edge flags
  `"enabled":false`), its parse proxy is 65% longer and its `prepare` 18%
  longer. Because the two servers build different structures (a catalog
  plus a 2,139-edge engine for L, a 19,991-edge engine for F), this figure
  mixes flag handling with a different build. It is not a clean cost of
  flags at equal volume.
- **Parse share.** The parse proxy is about 25% of L's import time. Most of
  the time goes to building the graph, which scales with registered edges.

## What this establishes (no verdict)

- The existing B4 reference imports only the effective graph, so it does not
  hold the capability L provides.
- Parsing and building the full registered volume in a plain server corresponds
  to 82–93% of L's excess over E, depending on the method. That indicates volume is the main driver. It does not show that
  L's own catalog-plus-engine build has the same cost structure.
- **L against F is +13.7%.** This diagnostic does not show that it is
  unavoidable. Candidates to examine are the flagged wire format (larger
  body, object-shaped node entries) and the catalog and flag handling in
  `prepare`. Neither was profiled here.
- **Departure from the plan.** The plan described F as "the same parse and
  storage volume, without flags". As noted above, F does not hold the same
  structures as L. The plan's "remaining build and publication time" is
  given only as the `prepare` and `publish` phases.
- Whether the full-topology volume cost is required is a property of the
  product contract. That is the maintainer's question, not a measurement.

## Limits

- One run, 12 pairs, on a laptop that was not gated.
- The phase figures come from one import per arm.
- The parse figure is a proxy: generic `Value` parsing, not the server's typed
  decoding.
