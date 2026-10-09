"""Report controlled BFS/DFS timings and independently collected structural work."""
import json,hashlib,statistics
from pathlib import Path
HERE=Path(__file__).resolve().parent
rows=json.loads((HERE/'comparison.json').read_text())['rows']
E=['traversal-bfs','traversal-dfs','compact-workspace','petgraph-dfs']
text='''# Controlled BFS versus LIFO search — 2026-10-05

## Contract and scope

These are **benchmark-only Knotrel controls**, not production engine options.
`traversal-bfs` and `traversal-dfs` share a snapshot of Compact's sorted adjacency,
BTreeMap ID translation, mutation implementation, u32 epoch marks and reusable
Vec scratch. Both mark on insertion and stop when an inspected neighbor equals
the target. DFS pops the last pending vertex; BFS advances a queue cursor.
This isolates FIFO/LIFO traversal and its inherent buffer-lifetime differences.
It does not reproduce petgraph's mark-on-pop DFS or its bitset/edge layout.

`compact-workspace` is a production-core anchor; `petgraph-dfs` is the external
context. The controls are not assumed binary-identical to the production BFS.
Every report labels the implementation. No default, server configuration or
production core API changed.

## Timed matrix

904 successful processes on one shared benchmark executable: 576 sparse, 288
dense, 16 extreme, 24 Cogentco. Sizes, seeds, workloads and operation traces
match the preserved traversal-scale study. Sparse: 1,024/10k/100k/1M, path/blocks,
10/50/90% queries; dense: 128/512 with one/two bridges; both fresh and warmed,
three independent processes per engine/cell. 10M uses only 50% queries and one
trial per engine/cell, so it remains exploratory. Cogentco uses the preserved
real topology with synthetic failures and three trials per regime.

Runtime is replay wall time, excluding graph setup; setup, whole-process peak
RSS and per-operation tails are retained in `comparison.json`. Fresh/warmed do
not mean hardware caches were flushed. Expected mutation/query results and exact
fingerprints are checked. New measurements never overwrite historical results.
Synthetic collection order is seeded shuffle, not perfect position balancing.

All deltas below are `100*(DFS/BFS-control - 1)`, so negative is less runtime.
Small sample counts and process variation limit close rankings. No confidence
interval or universal speedup is claimed. We do not pool per-operation percentiles.

| Family | Cells | DFS lower-runtime cells | Runtime delta range | Median cell delta |
|---|---:|---:|---:|---:|
'''
for family in ['sparse','dense','extreme','cogentco']:
 ds=[r['engines']['traversal-dfs']['runtime_delta_vs_bfs_percent'] for r in rows if r['family']==family]
 text+=f'| {family} | {len(ds)} | {sum(d<0 for d in ds)} | {min(ds):+.2f}% to {max(ds):+.2f}% | {statistics.median(ds):+.2f}% |\n'
text+='''
Equal-weight summaries are descriptive, not production workload weights. Extreme
is excluded from any general recommendation. Inspect ranges before reading a
small median difference as a stable effect.

## Warmed 50% query scenarios and real topology

Workspace and petgraph percentages also use the **BFS control** denominator.

| Family / topology | N | BFS ms | DFS delta | Core Workspace delta | petgraph delta |
|---|---:|---:|---:|---:|---:|
'''
for r in rows:
 if r['regime']=='warmed' and (r['query_percent']==50 or r['family']=='cogentco'):
  es=r['engines'];text+=f"| {r['family']} / {r['workload']} | {r['nodes']} | {es[E[0]]['metrics']['runtime_ns']['median']/1e6:.3f} | "+' | '.join(f"{es[e]['runtime_delta_vs_bfs_percent']:+.2f}%" for e in E[1:])+' |\n'
text+='''
## Structural diagnostics

The separate `traversal-profile` binary instantiates `COUNT=true`; timed adapters
use `COUNT=false`, removing counter increments at compile time. Diagnostic results
contain **no timing measurements**. Counters measure expanded vertices (not
necessarily all discovered vertices), inspected adjacency entries, peak pending
frontier and peak Vec length. BFS retains expanded queue entries until query end;
DFS pops them. Vector length is not allocated capacity, heap bytes or process RSS.
No answer cache is used, and diagnostic state is reset for every query.

Diagnostics replay each synthetic scenario twice, require byte-identical output,
and match the timing fingerprint. Both searches assert each independent expected
answer against the same graph state. Cogentco has timings but no structural probe
in this version. Aggregate work is not sufficient to attribute cache behavior or
all execution-time changes to a single cause. Detailed per-query counts remain
available for true/false separation.

| Topology | N | Query % | DFS/BFS expanded delta | DFS/BFS examined arcs delta | BFS / DFS peak buffer length |
|---|---:|---:|---:|---:|---:|
'''
dm=json.loads((HERE/'diagnostics/manifest.json').read_text())
for c in dm['cases']:
 r=json.loads((HERE/'diagnostics'/(c['name']+'.json')).read_text());qs=r['queries']
 for q in qs:
  if not q['expected']:
   assert q['bfs']['expanded_vertices']==q['dfs']['expanded_vertices']
   assert q['bfs']['examined_arcs']==q['dfs']['examined_arcs']
 def sums(field):return [sum(q[e][field] for q in qs) for e in ['bfs','dfs']]
 v=sums('expanded_vertices');a=sums('examined_arcs');peaks=[max(q[e]['peak_buffer_len'] for q in qs) for e in ['bfs','dfs']]
 text+=f"| {r['workload']} | {r['config']['nodes']} | {r['query_percent']} | {100*(v[1]/v[0]-1):+.2f}% | {100*(a[1]/a[0]-1):+.2f}% | {peaks[0]} / {peaks[1]} |\n"
text+='''
For false queries the diagnostic checks equal expanded-vertex and examined-arc
counts, since both searches must exhaust the reachable component. True queries
can terminate in different places; DFS does not promise a shortest path.


## Decision

Do not replace production BFS with this DFS. It is slower in 35/48 sparse cells,
while its small dense differences are mixed and the Cogentco gains are specific
to one topology. Against actual core Workspace, the warmed Cogentco improvement
is 32.24%; against the BFS control it is 38.12%. These denominators must not be
interchanged. Keep both controls for investigation, not as server options.

On warmed cyclic blocks at 1M vertices and 50% queries, DFS takes 78.60% more
runtime than the BFS control. Diagnostics show only 0.69% more expanded vertices
and 0.73% more inspected arcs. Therefore extra traversal count alone does not
account for the magnitude of this timing gap. Access order, stack/queue behavior
and compiled-code effects remain plausible but unmeasured contributors; there
are no hardware cache-miss or allocation-count measurements here.

The BFS control itself differs measurably from production Workspace (for example,
19% on that cell), so this is a controlled experimental comparison, not a claim
that replacing a production method yields the reported percentage. Both anchors
are retained in every cell. petgraph's advantage cannot be credited to DFS alone:
it combines different mark timing, bitset storage and adjacency representation.
A next controlled experiment can hold BFS fixed and vary epoch marks versus a
packed bitset; that optimization is not implemented or claimed by this report.

## Reproduction and validation

`collect.py` and `collect_real.py` preserve commands, binary/source hashes,
compiler, environment, dirty source patches and new Rust files. `analyze.py`
checks cardinalities, artifact hashes, source/binary equality, fingerprints and
answer counts before ranking. `collect_diagnostics.py` records the separately
built profiler identity and source hashes. Diagnostics may have a later source
snapshot than the timed executable because the legacy-workload fingerprint fix, its test and CLI help text
were finalized after the timed collection; traversal kernels are unchanged.

Tests cover independent matrix-oracle histories for every engine, early exits,
cut/relink, unknown/full-width IDs, epoch rollover and known structural counts.
The CLI comparison checks all registered engines. Formatting, all-target Clippy
with warnings denied, workspace tests/doctests and Rustdoc with warnings denied
passed before delivery, including a regression test for legacy/sustained profiler trace identity. Instrumented values are never mixed into runtime
ranking. The previous source audit's claim that Compact used swap removal has
been corrected: Compact uses binary search and shifts in sorted neighbor vectors.
'''
(HERE/'README.md').write_text(text)
detail='''# All timing cells

Each engine row is median runtime and observed range, delta against BFS control,
setup, peak whole-process RSS and operation tails. No pooled percentiles.

'''
for r in rows:
 detail+=f"## {r['family']} / {r['workload']} / N={r['nodes']} / q={r['query_percent']} / {r['regime']}\n\n"
 detail+='| Engine | Trials | Runtime ms [min,max] | Delta | Setup ms | RSS MiB | Cut p95/p99 µs | Query p95/p99 µs |\n|---|---:|---|---:|---:|---:|---|---|\n'
 for e in E:
  v=r['engines'][e];m=v['metrics'];w=m['runtime_ns']
  def tail(op):return '—' if m[op+'_p95_ns'] is None else f"{m[op+'_p95_ns']['median']/1000:.3f}/{m[op+'_p99_ns']['median']/1000:.3f}"
  detail+=f"| {e} | {v['trials']} | {w['median']/1e6:.3f} [{w['min']/1e6:.3f},{w['max']/1e6:.3f}] | {v['runtime_delta_vs_bfs_percent']:+.2f}% | {m['setup_ns']['median']/1e6:.3f} | {m['rss_bytes']['median']/2**20:.2f} | {tail('cut')} | {tail('connected')} |\n"
 detail+='\n'
(HERE/'details.md').write_text(detail)
(HERE/'artifact-sha256.json').write_text(json.dumps({p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(HERE.iterdir()) if p.is_file() and p.name!='artifact-sha256.json'},indent=2)+'\n')
