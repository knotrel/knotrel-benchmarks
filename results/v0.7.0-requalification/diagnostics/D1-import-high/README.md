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
| L | lifecycle | full registered topology with flags | 10,000 nodes, 19,991 registered edges, flags |
| F | plain | full registered topology, everything active | the same nodes and edges, no flags |
| E | plain | effective graph only, plus the application flag store (the B4 reference) | 10,000 nodes, 2,139 effective edges |

F holds the full volume but not the flags, so it cannot answer the
effective-graph connectivity that L answers. It isolates volume from flags.
It is not a drop-in alternative to L.

## Results (`raw/d1.jsonl`)

| | L | F | E |
|---|---|---|---|
| Median import time (incl. E's flag store) | 2.335 ms | 2.006 ms | 0.467 ms |
| Body bytes | 985,340 | 744,252 | 141,320 |
| Parse-only proxy (`sonic_rs::Value`, median of 25) | 0.578 ms | 0.351 ms | 0.086 ms |
| Server `prepare` phase (one metrics-enabled import) | 2.172 ms | 1.845 ms | 0.313 ms |
| Server `publish` phase | 0.018 ms | 0.014 ms | 0.009 ms |

Paired ratios over the 12 pairs (median, min–max):

| Ratio | Median | Range | Meaning |
|---|---|---|---|
| L / E | 4.96 | 4.18–5.71 | the B4 comparison (+396%; a3-3 measured +413%) |
| F / E | 4.42 | 3.71–4.92 | storing and parsing 9.3× more edges, no flags |
| L / F | 1.137 | 1.078–1.215 | flags and lifecycle at equal volume |

## Breakdown

- **Volume.** Of L's 3.96× excess over E, about 3.42× (86%) comes with F as
  well: importing the 17,852 non-effective registered edges that the
  full-topology contract keeps, against the reference's 2,139. The body is
  5.3× larger (F against E), and server `prepare`, which covers parse and
  build, is 5.9× longer.
- **Flags and lifecycle.** At equal volume, L costs +13.7% (7.8–21.5%) over
  F. Its body is 32% larger than F's: the node objects
  `{"node":…,"active":false}` and the edge flags `"enabled":false`. The parse
  proxy is 65% longer, and `prepare` 18% longer.
- **Parse share.** The parse proxy is about 25% of L's import time. Most of
  the time goes to building the graph, which scales with registered edges.

## What this establishes (no verdict)

- The existing B4 reference imports only the effective graph, so it does not
  hold the capability L provides. Most of the measured overhead, about 86%,
  is the cost of holding the full registered topology. A plain server shows
  the same cost when given the same volume.
- **The remaining part, flags and lifecycle at equal volume, is about +14%.**
  This diagnostic does not show that it is unavoidable. Candidates to examine
  are the flagged wire format (larger body, object-shaped node entries) and
  the flag handling in `prepare`. Neither was profiled here.
- Whether the full-topology volume cost is required is a property of the
  product contract. That is the maintainer's question, not a measurement.

## Limits

- One run, 12 pairs, on a laptop that was not gated.
- The phase figures come from one import per arm.
- The parse figure is a proxy: generic `Value` parsing, not the server's typed
  decoding.
