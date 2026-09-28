# Exact dynamic forest: scale, churn and memory — 2026-09-27

The opt-in `ett-scan` prototype maintains an AVL Euler-tour spanning forest and
scans non-tree edges on the smaller side after a tree cut. It is exact and has
O(log V) worst-case connectivity queries; it is **not HDT**. The default production
Graph and HTTP service remain compact BFS. Petgraph 0.8.3 is the practical external
baseline; no results for Differential Dataflow, Memgraph or GraphScope are claimed.

## What was run

Apple M3 / macOS aarch64, Rust 1.98.1, release thin LTO / one codegen unit.
Core dependencies unchanged. Source snapshots, collector, commands and executable
hashes are preserved with each collection. All cases run sequentially, one backend
per process; configuration order is shuffled with seed 42. Graphs are rebuilt for
warmup and measurement. Each process has one measured replay. Two process trials
are used except the million-node extension, which has only one per configuration.

| Collection | Nodes | Base operations/replay | Query percentages | Replay regimes | Processes |
| --- | --- | ---: | --- | --- | ---: |
| This scale matrix | 10,000 / 100,000 | 2,000 | 10 / 50 / 90 / 99 | fresh and warmed | 192 |
| [Million-node extension](../2026-09-27-forest-million/README.md) | 1,000,000 | 2,000 | 10 / 50 / 90 / 99 | fresh and warmed | 48 |
| [Long histories](../2026-09-27-forest-long/README.md) | 10,000 | 100,000 | 50 / 99 | warmed | 24 |
| [Immediate-repeat sensitivity](../2026-09-27-forest-repeats/README.md) | 100,000 | 2,000 plus repeats | 50 / 99 | fresh and warmed | 48 |

Both sustained families are included everywhere. Path toggles path edges; blocks
are cycles of at most 16 vertices joined by bridges. Internal cycle changes keep
each block connected while bridges split/join blocks. State persists across
rounds. Expected connectivity comes from missing boundary intervals, independently
checked by matrix closure on small graphs; every timed answer is checked.

Fresh means zero deliberate warmups; warmed means one complete unreported replay.
Neither flushes CPU, allocator or OS caches. Extra immediate queries are zero
except in the repeat collection, where one is separately timed after each base
query. CPU frequency, affinity, temperature and background load are uncontrolled.

Peak RSS is for the **whole process**, including generation, trace JSON export,
engine, samples, allocator retention and any warmup. It is not engine-only heap.
Setup measures vertex registration, backend creation and initial edges; it also
includes the adapters' registration-validation map. Base operation totals exclude
setup, repeats, checking and teardown. Loading can reverse an operation-only win.

## At 100,000 vertices

Warmed values below are medians of two process summaries. Query/cut columns are
medians of per-process p50/p99, not pooled percentiles or confidence intervals.
Raw trials, all four ratios, fresh results and maxima remain in `summary.csv`.
At 99%, 2,000 operations contain only 20 updates (often all cuts), so cut p99 is
essentially the maximum of a small sample, not a production tail estimate.

| Family | Query % | Backend | Base ops ms | Setup ms | Query p50 µs | Cut p99 µs | Peak process RSS MiB |
| --- | ---: | --- | ---: | ---: | ---: | ---: | ---: |
| blocks | 50 | compact-bfs | 7.087 | 19.530 | 3.604 | 1.417 | 16.8 |
| blocks | 50 | ett-scan | 10.440 | 152.971 | 0.895 | 97.001 | 80.3 |
| blocks | 50 | petgraph-dfs | 10.076 | 15.482 | 3.500 | 0.709 | 14.1 |
| blocks | 99 | compact-bfs | 139.308 | 33.553 | 53.646 | 1.521 | 17.2 |
| blocks | 99 | ett-scan | 3.968 | 155.131 | 0.875 | 343.604 | 80.0 |
| blocks | 99 | petgraph-dfs | 232.039 | 7.852 | 89.855 | 1.188 | 14.1 |
| path | 50 | compact-bfs | 6.641 | 18.570 | 3.083 | 0.688 | 16.8 |
| path | 50 | ett-scan | 7.310 | 147.805 | 1.062 | 50.229 | 78.9 |
| path | 50 | petgraph-dfs | 4.716 | 6.707 | 2.021 | 0.438 | 13.8 |
| path | 99 | compact-bfs | 137.796 | 19.989 | 49.354 | 0.938 | 17.5 |
| path | 99 | ett-scan | 4.355 | 146.380 | 0.896 | 569.104 | 76.9 |
| path | 99 | petgraph-dfs | 105.301 | 6.978 | 39.937 | 0.812 | 13.8 |

The forest wins the operation-only comparison at 90% and 99% queries in both
100k families; it loses to compact BFS at 10% and 50%. On the 99% traces it takes
roughly 4 ms versus 138–139 ms for compact BFS, but setup is roughly 150 ms rather
than 19 ms. Therefore the short experiment does not establish a lifecycle win.
The warmed 100k forest processes peak around 77–80 MiB, versus roughly 17 MiB for
compact BFS and 14 MiB for petgraph, with the process-scope caveat above.

## What the larger and longer runs change

At one million nodes and 99% queries (one warmed trial per family), forest query
p50 is 2.2–2.8 µs. Base operations take 31 ms on the path and 68 ms on blocks,
compared with compact BFS's 1,422 ms and 993 ms. However forest setup takes
2.3–2.5 seconds, and cut p99 reaches 6.9 ms / 25.0 ms. Setup plus base operations
is slower than compact BFS for both short replays. Peak process RSS varies strongly
with backend and warmup; see every trial rather than inferring an engine memory
ratio from a single million-node process.

On 100,000-operation histories at 10k nodes, the forest still loses at 50% queries:
34/65 ms (path/blocks) versus compact BFS 24/40 ms and petgraph 12/26 ms. At 99%,
it wins the operation-only comparison: 18/19 ms versus compact BFS 99/113 ms and
petgraph 58/100 ms. The longer 50% traces contain tens of thousands of both links
and cuts, so their result is not merely the initial deletion transient.

The path family has no non-tree candidates: its tree-cut cost exposes enumeration
of the smaller component alone. Blocks additionally expose candidate search and
replacement. For example, the 100k/50% block trace enumerates 561,273 vertices,
checks 58,590 non-tree incidences and promotes 452 replacements over 928 tree cuts.
Counters reflect the implemented enumeration order and are reset after loading.

## Interpretation and next engineering decision

Keep the prototype opt-in. The experiment demonstrates the value of maintained
connectivity for query-heavy traces, not a universally faster engine. A useful
next change should target expensive tree deletions and memory rather than merely
making already cheap queries cheaper. HDT levels address repeated replacement
searches; Cluster Forest is a candidate when memory is decisive. Neither is
implemented or selected by this experiment.

Before promoting a maintained index, add dense/redundant graphs, degree skew,
controlled replacement-search adversaries, stable edge-count churn and real query
locality. The current sparse models tend to fragment: the query percentage also
changes how many mutations have occurred. They do not establish a universal
crossover ratio or size. No growing-node latency, HTTP concurrency or monetary
cost benchmark is provided; growing IDs and shared reads are correctness-tested.

## Reproduction

```sh
python3 scripts/run_scale.py results/NEW_DIRECTORY --nodes 10000 100000 --query-percent 10 50 90 99 --rounds 20 --trials 2 --regimes fresh warmed
python3 scripts/summarize_scale.py results/NEW_DIRECTORY
```

The collector uses `/usr/bin/time` for process RSS; on this Mac those statistics
require execution outside the filesystem sandbox. A failed sandboxed smoke test
was retained under `/private/tmp`, not included as a successful measurement.
Timeouts terminate the entire measurement process group and preserve partial
failure output. There were no failed/timed-out cases in these four completed
collections. See [verification](verification.md) for source/artifact hash audits,
correctness checks and independent review. No commits or pushes were made.
