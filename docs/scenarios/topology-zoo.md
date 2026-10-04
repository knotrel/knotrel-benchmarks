# Topology Zoo import and replay

Implemented: Python standard-library adapter and Rust `--trace-in` replay.
[Abilene integration run](../../results/2026-10-03-topology-import-smoke/README.md)
checks a pinned real topology across four engines. This is not a scale study.

## Reproduce the input

Retrieve only the following file, preserving its bytes:

- [Abilene.graphml at revision 51118849b99534f01010d885d66321433a7eef9e](https://raw.githubusercontent.com/mroughan/InternetTopologyZoo/51118849b99534f01010d885d66321433a7eef9e/graphml/Abilene.graphml)
- SHA-256: `8cd694280d98b336bb9b51fc3b2129a514f1b1b1ac80f2022aca02a57ef1e371`
- [CC-BY-4.0 license at the same revision](https://raw.githubusercontent.com/mroughan/InternetTopologyZoo/51118849b99534f01010d885d66321433a7eef9e/LICENSE)
- License SHA-256: `ea6250adc8affe14f68e97532da2ae64224d31e13363c9c89040810cbd8c06c9`
- Attribution: Knight, Nguyen, Falkner, Bowden and Roughan, *The Internet Topology
  Zoo*, IEEE JSAC 29(9), 1765–1775 (2011), DOI 10.1109/JSAC.2011.111002.

Put the GraphML outside Git, for example `/tmp/Abilene.graphml`. Record your actual
retrieval date. The following command records the original acquisition date for
byte-identical reproduction of our trace (change it for a new acquisition):

```sh
python3 scripts/import_topology_zoo.py /tmp/Abilene.graphml \
  --output /tmp/abilene.trace.json \
  --sha256 8cd694280d98b336bb9b51fc3b2129a514f1b1b1ac80f2022aca02a57ef1e371 \
  --source-url https://raw.githubusercontent.com/mroughan/InternetTopologyZoo/51118849b99534f01010d885d66321433a7eef9e/graphml/Abilene.graphml \
  --source-revision 51118849b99534f01010d885d66321433a7eef9e \
  --retrieved-date 2026-10-03 --license CC-BY-4.0 \
  --citation 'Knight et al., The Internet Topology Zoo, IEEE JSAC 2011, doi:10.1109/JSAC.2011.111002' \
  --failures 10 --seed 42 --queries 8

cargo run --release --locked -- \
  --trace-in /tmp/abilene.trace.json \
  --engine compact-bfs,ett-scan,hdt,petgraph-dfs \
  --warmup 1 --repetitions 3 --query-repeats 2
```

Both adapter output and runner `--trace-out` refuse to overwrite files. No network
access occurs in the adapter. The supplied source checksum is verified; provenance
strings are caller assertions, not authenticated evidence of license or origin.

## Normalization and oracle

Only UTF-8, namespaced GraphML containing one flat undirected graph is supported.
Reject duplicate node/edge IDs, unknown endpoints, nested graphs, directed edges,
hyperedges, ports, external references and DTD/entity declarations. Preserve every
node, including isolates. Sort original IDs by UTF-8 bytes; their array positions
are dense IDs. Edge IDs use `id:SOURCE_ID`; missing IDs use `index:SOURCE_POSITION`.
Preserve each non-loop physical link separately, sort identities, and record them.
Self-loops are discarded with a count. Metadata has no effect on connectivity;
retain the original artifact for node attributes and map provenance.

Shuffle physical-link indices with descending Fisher–Yates, using wrapping u64
LCG `state = state * 6364136223846793005 + 1442695040888963407` and `state % bound`.
Modulo bias is accepted and documented; this is not uniform statistical sampling.
Fail the first `--failures` links in permutation order, then repair in reverse.
Maintain pair reference counts to emit only effective cuts/links. Each batch
queries `(0,n-1)` plus `--queries` seeded distinct endpoint pairs with replacement
across queries. The same LCG stream continues after the shuffle: draw source modulo
n, target modulo n-1, increment target when target >= source. Default seed is 42,
default seeded pairs per batch is 8; zero permits a fixed-probe-only variant.

The generator rebuilds union-find from active **source links** for each batch's
expected answers. The Rust loader independently replays normalized mutations and
validates all answers with BFS before warmup or operation timers. Synthetic tests
compare all pairs on a cycle, bridge and isolate, plus parallel physical links.
The loader does not independently re-fetch/re-interpret the original GraphML.

This first adapter prioritizes auditability for small topology archives. It loads
input and trace in memory, rebuilds source components per batch, and counts initial
projected bridges by removal experiments. It is not a streaming million-edge
preprocessor. Parsing/projection/serialization cost is not included in kernel
latencies and is not yet separately instrumented. No peak-memory claim is made.

## Import schema 1 and report schema 4

The import envelope has exactly these fields:

| Field | Contract |
| --- | --- |
| `schema_version`, `kind` | `1`, `"connectivity-import"` |
| `workload` | Nonempty versioned scenario name |
| `node_ids` | At least two sorted, unique, nonempty source-ID strings |
| `provenance` | Nonempty `source_url`, `source_revision`, `license`, `citation`, `retrieved_date`; 64 hexadecimal digits in `source_sha256` |
| `transform` | Nonempty object of scenario-specific parameters, counts and source-link identities; retained without scenario-specific validation by the generic loader |
| `batches` | `{time,start,end}`; strictly increasing u64 logical times, contiguous nonempty half-open operation ranges covering the complete trace |
| `trace` | `initial_edges` and `operations`, using the existing link/cut/connected operation fields |

Unknown envelope, provenance, batch, trace and operation fields are rejected.
Initial edges are unique canonical pairs. Mutation endpoints must be canonical
and distinct; every operation references registered IDs. Each batch has sorted
cuts, sorted links, then at least one query. A pair cannot be cut and linked in
one batch: only net transitions are allowed. Query `expected` is checked by BFS.
There is no partial reporting on input validation failure.

`--trace-in` rejects `--nodes`, `--rounds`, `--seed`, `--workload` and
`--query-percent`; these would misrepresent the imported experiment. Replay,
engine and repeat options remain available. Optional `--trace-out` copies exact
input bytes, including whitespace; the FNV diagnostic fingerprint covers these
bytes. Use an external SHA-256 for artifact integrity.

Imported individual reports use schema 4, omit generated `config`, and add
`import`: node count, source-batch count, provenance, transform, validated query
count, load/parse time and validation time. Multi-engine reports retain the schema
3 comparisons envelope. Existing generated trace schema 1 and report schema 2
are unchanged. Historical result-summary scripts are not extended to schema 4;
consume its explicit import metadata rather than assuming generated rounds.

Validation runs once before all backends. Input cache state is recorded as
uncontrolled. Fresh-graph repetitions do not imply cold hardware caches. Query
repeats are separately reported. For comparative studies rotate engine order and
use fixed-only and varied-pair schedules as separate trace variants.
