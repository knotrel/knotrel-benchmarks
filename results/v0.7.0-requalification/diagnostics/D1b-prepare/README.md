# D1b: import `prepare` sub-phase profile (item 1, phase 2)

This diagnostic follows DIAGNOSTICS-PLAN-2.md, D1b. It is not part of the
qualification. The a3-3 verdict for B4 `import-high` stands: REGRESSION
+413.26% [+375.24, +446.79] against a 100% tolerance. No threshold changes.

**Setup.**
- **Build:** diagnostic build of candidate e75ff6a with `d1b-instrument.diff`.
  It adds process-wide accumulators at sub-phase boundaries: about 20 clock
  reads per import.
- **Harness:** `harness/`. The binary is in `raw/binary-sha256.txt`.
- **Inputs and arms:** as in D1 (sparse 10k, seed 5000001, 60% inactive,
  30% disabled):
  - **L:** lifecycle server, full topology with flags;
  - **F:** plain server, full topology, everything active;
  - **E:** plain server, effective graph only.
- **Rounds:** 30 analyzed after 3 warmup, in rotating order, with a fresh
  server per import. One run on the developer laptop, not gated.
- **Outputs:** `raw/d1b.jsonl`. `summary.txt` is produced by `summarize.py`.

**Difference from D1.** E here is the server import alone. D1 also timed the
B4 reference's application flag store inside E's window. Ratios against E are
therefore larger here: L/E is 6.37 here, against 4.96 in D1.

## Results (median per import, µs; `summary.txt`)

| Sub-phase | L | F | E | What it is |
|---|---|---|---|---|
| Parse (typed `parse_import_body`) | **937.6** | 711.4 | 161.5 | JSON decoding into request structs |
| Spec conversion | 10.4 | — | — | wire to `NodeSpec`/`EdgeSpec` |
| Catalog: node pass | 54.2 | — | — | hash insert of 10,000 nodes with flags |
| Catalog: edge counting (+ self-loop and limit checks) | 58.1 | — | — | 2 endpoint probes per registered edge |
| Catalog: incident allocation | **198.1** | — | — | one `Vec` allocation per registered node |
| Catalog: fill | 93.2 | — | — | 2 incidence pushes per registered edge |
| Sort and dedup (+ conflict check) | **242.2** | — | — | per-node sort of incident lists |
| `finish` counts and shrink | 81.6 | — | — | catalog walk and counts |
| Effective engine: ID sort and index | 93.3 | — | — | |
| Effective engine: adjacency allocation | 96.5 | — | — | |
| Effective engine: effective-edge pass | 128.9 | — | — | catalog probe per enabled incidence |
| Effective engine: `from_sorted_adjacency` | 26.3 | — | — | |
| Plain engine: `add_node` loop | — | 69.9 | 65.2 | |
| Plain engine: `link` loop | — | **936.1** | 73.0 | 19,991 links in F, 2,139 in E |
| Publish (lock, checks, swap, log, drop) | 16.2 | 14.8 | 8.1 | |
| **Import total** | **2,080.1** | **1,775.1** | **327.1** | sub-phase coverage 98.3% / 97.8% / 94.8% |

The per-arm min–max over rounds is in `summary.txt`; pair min–max is given
for the ratios. Ratios: L/F 1.172 (1.052–1.307), F/E 5.40, L/E 6.37. L/F
is 1.137 in D1, a different run with different harness timing (D1 also timed
E's flag store).

Grouped (µs):

| Group | L | F | E |
|---|---|---|---|
| Parse | 937.6 | 711.4 | 161.5 |
| Graph construction | 1,071.3 (catalog 401.5, sort/dedup 242.2, finish 81.6, effective engine 346.0) | 1,011.9 | 137.9 |
| Other (checks, spec, publish) | 26.7 | 14.9 | 8.2 |

## What this demonstrates

1. **Parse is 45% of L's import and most of L − F.**
   - L − F is about +305 µs. Of that, parse is +226 µs, construction +59 µs,
     and spec conversion and publish about +11 µs.
   - Parse throughput is about 1.05 GB/s in L and F (L 985 KB in 938 µs,
     F 744 KB in 711 µs), and 0.87 GB/s in E (141 KB in 162 µs).
   - So between L and F the extra parse time is roughly proportional to the
     body bytes added by the flagged wire format: object-shaped inactive
     nodes, and `"enabled":false`.
2. **Construction costs about the same in L and F, but for different work.**
   - L builds a catalog of the 19,991 registered edges plus a
     2,139-edge effective engine: 1,071 µs.
   - F builds a plain engine of 19,991 edges: 1,012 µs.
   - Both scale with registered volume. As the maintainer noted, L/F does not
     identify a removable cost by itself. Here, construction accounts for
     only about 59 µs of the difference.
3. **L − E (about 1,753 µs) by group:**
   - parse +776 µs (registered volume and flags in the body);
   - catalog, sort and finish +725 µs (holding the registered topology);
   - effective engine +208 µs over E's plain build of the same effective
     graph (ID sort, plus catalog probes during the effective pass).

## Classification (none proven reducible: no variant measured)

| Cost | Class | Reasoning |
|---|---|---|
| Parse, roughly proportional to bytes (L, F) | **inherent to the wire format** | Reducing it needs a more compact flag encoding, which is an API/contract change, or a faster decoder (not examined). |
| Catalog holding the registered topology | **inherent** in some form (the contract keeps registered entries) | |
| Incident allocation, one `Vec` per node (198 µs) | **implementation, plausible** | Mechanism: one arena or CSR allocation. It conflicts with per-node mutation in place, so the trade-off is unmeasured. |
| Sort and dedup (242 µs) | **unclear** | Sorted incident lists serve lookups and duplicate detection. Cheaper alternatives (radix sort, trusting already-sorted input) are hypotheses. |
| Effective engine: ID sort and probes (about 208 µs over E) | **implementation, plausible** | Mechanism: assigning indices during the catalog pass. Unmeasured. |
| `finish` walk (82 µs) | **implementation, plausible** | It could be folded into earlier passes. Unmeasured. |

The "implementation, plausible" sites together come to about 490 µs of L's
2,080 µs. The sum mixes two absolute costs (198 and 82 µs) with one cost
relative to E (208 µs). It is an upper bound on what they could save, not an
estimate.
Even eliminating all of them would leave L/E far above the 2× tolerance
(+100%): (2,080 − 490) / 327 ≈ 4.9 against E here. Parse and catalog volume
dominate.

## Limits

- One run of 30 rounds, on a laptop that was not gated.
- The instrumentation adds about 20 clock reads per import to every arm.
- Sub-phase coverage is 95–98%; the rest is request routing and the
  blocking-pool hop.
