"""Report a same-build epoch/bitset experiment; never infer heap from process RSS."""
import hashlib,json,statistics
from pathlib import Path
HERE=Path(__file__).resolve().parent
rows=json.loads((HERE/'comparison.json').read_text())['rows']
E=['traversal-bfs','traversal-bitset','compact-workspace','petgraph-dfs']
old=json.loads((HERE.parent/'2026-10-05-traversal-order/comparison.json').read_text())['rows']
key=lambda r:(r['family'],r['workload'],r['nodes'],r['query_percent'],r['regime'])
previous={key(r):r for r in old}
drift=[]
for r in rows:
 p=previous[key(r)];assert p['fingerprint']==r['fingerprint']
 before=p['engines']['traversal-bfs']['metrics']['runtime_ns']['median'];now=r['engines']['traversal-bfs']['metrics']['runtime_ns']['median']
 drift.append({'cell':key(r),'historical_epoch_ns':before,'current_epoch_ns':now,'drift_percent':100*(now/before-1)})
(HERE/'baseline-drift.json').write_text(json.dumps(drift,indent=2)+'\n')
text='''# BFS epoch marks versus packed bitset — 2026-10-05

## Controlled change

This is a **benchmark-only** experiment. `traversal-bfs` uses reusable u32 epoch
marks; `traversal-bitset` uses reusable u64 words, one bit per vertex, cleared for
each non-reflexive query. Both use the same sorted adjacency, BTreeMap ID lookup,
mutation code, FIFO queue, marking on insertion and early target detection.
Queue and graph representation are unchanged. No connectivity answers are cached.
No production core API, default backend or server configuration was changed.

This custom bitset is not copied from petgraph and is not a claim to reproduce
its implementation. petgraph remains a DFS/bitset/edge-arena context baseline;
production `compact-workspace` is an anchor beside both experimental controls.
Controls are not assumed performance-identical to the production Workspace.

## Measurement contract

One release binary, 904 timed processes: 576 sparse, 288 dense, 16 extreme and
24 Cogentco. Sparse sizes are 1,024, 10k, 100k, 1M; paths and cyclic blocks;
10/50/90% queries; fresh/warmed; three process trials per engine/cell. Dense uses
128/512 vertices and one/two inter-clique bridges. Cogentco reuses the real
197-vertex topology with synthetic outages. 10M is one trial per cell, 50% queries
only, and is **exploratory**. All synthetic traces retain ten rounds and seed 42.

Runtime means median replay wall time including dispatch/checks/sampling but
excluding setup. Bitset reset is inside each timed non-reflexive query. Epoch
initial growth is also inside the first such query; rollover is tested but not
reached in this short campaign. Warmup recreates the graph and scratch before
measurement; it does not preallocate the measured workspace or flush hardware
caches. Cases execute sequentially in seeded shuffle order, not strict position
balance. Per-process operation percentiles are summarized, never pooled.

The before/after denominator is **epoch BFS in this same build**, not historical
timings. The prior DFS campaign is preserved; `baseline-drift.json` gives its
unchanged-trace epoch timing drift separately. Do not multiply historical speedups
to manufacture a current ranking. All metrics and unfavorable cases are retained.

## Runtime outcome

Delta = `100*(bitset/epoch - 1)`; negative means lower replay time. Cell summaries
are descriptive and equally weighted, not a production mix or confidence interval.

| Family | Cells | Bitset lower-runtime cells | Delta range | Median cell delta |
|---|---:|---:|---:|---:|
'''
for family in ['sparse','dense','extreme','cogentco']:
 ds=[r['engines'][E[1]]['runtime_delta_vs_bfs_percent'] for r in rows if r['family']==family]
 text+=f'| {family} | {len(ds)} | {sum(d<0 for d in ds)} | {min(ds):+.2f}% to {max(ds):+.2f}% | {statistics.median(ds):+.2f}% |\n'
text+='''
## Warmed 50% query examples

All three percentage columns use the experimental epoch BFS denominator.

| Family / topology | N | Epoch ms | Bitset delta | Production Workspace delta | petgraph delta |
|---|---:|---:|---:|---:|---:|
'''
for r in rows:
 if r['regime']=='warmed' and (r['query_percent']==50 or r['family']=='cogentco'):
  es=r['engines'];text+=f"| {r['family']} / {r['workload']} | {r['nodes']} | {es[E[0]]['metrics']['runtime_ns']['median']/1e6:.3f} | "+' | '.join(f"{es[e]['runtime_delta_vs_bfs_percent']:+.2f}%" for e in E[1:])+' |\n'
text+='''
## Memory mechanism, not a process-memory promise

Logical mark payload is `4*N` bytes for epochs and `8*ceil(N/64)` bytes for bitsets:
approximately 32x smaller. This excludes Vec headers/capacity slack, allocator
metadata, BFS queue, graph, trace and harness. At 10M nodes this is 40,000,000
versus 1,250,000 bytes. The queue remains identical and may dominate scratch.
Process RSS in the detailed results includes all setup, traces and warmups;
it must not be interpreted as engine heap or marker allocation size.

Bitset clears every retained word on each non-reflexive query, even when only a
small component is reachable. Epoch marks usually avoid this reset but touch
larger entries during the visit. This is the expected tradeoff, not an attribution
of measured time to CPU caches: no hardware cache-miss or allocation profiler ran.

## Structural diagnostics

The separate `traversal-profile` uses COUNT=true; timed adapters use COUNT=false.
For each of 38 synthetic scenarios, two diagnostic runs must produce identical
output and match the timed fingerprint. Every query asserts exact expected
answers and **equal BFS/bitset expanded vertices, inspected arcs, peak pending
frontier and peak buffer length**. Diagnostic output contains no timing results.
Cogentco is timed but not structurally instrumented here. Peak vector length is
not allocated capacity. The retained DFS diagnostics are context only.

'''
d=HERE/'diagnostics';m=json.loads((d/'manifest.json').read_text());queries=0
for c in m['cases']:
 r=json.loads((d/(c['name']+'.json')).read_text())
 for q in r['queries']:assert q['bfs']==q['bitset'];queries+=1
for name,h in m['artifact_sha256'].items():assert hashlib.sha256((d/name).read_bytes()).hexdigest()==h
text+=f'Validated {queries:,} query comparisons across 38 scenarios, each replayed twice (76 diagnostic executions).\n\n'
text+='''
## Decision

Keep generation marks as the production Workspace strategy. In this campaign
bitset is slower in 40/48 sparse cells (median cell delta +3.19%), dense differences
are small and mixed (median +0.61%), and Cogentco is +1.81% warmed / +4.47% fresh
against the epoch control. Limited process trials do not establish significance
for close differences. This evidence does not justify a default or production
API change; it does not prove packed bitsets are universally inferior either.

Keep the bitset adapter as a reproducible memory/time tradeoff reference. At 10M,
mark payload falls from 40MB to 1.25MB, but observed whole-process RSS does not
consistently fall: in the single warmed path observation it increases from about
1,512 to 1,582 MiB. This is why mark-size arithmetic must not be presented as
measured process-memory savings. Extreme results are exploratory, not replicated.

Since per-query structural work is identical, the elapsed differences arise
outside a change in the chosen BFS traversal: marker/reset implementation and
associated compiled-code/access effects are candidates. This experiment cannot
assign individual CPU cycles to clearing, bit operations or cache behavior.
Neither switching to DFS nor replacing epochs with this bitset reproduces a
universal petgraph advantage. The next investigation should profile the remaining
adjacency/access costs before introducing another production strategy.

## Reproduction and checks

`collect.py` and `collect_real.py` retain exact arguments, revisions/dirty state,
source and binary hashes, compiler and build settings. New output directories
are mandatory; 120-second process timeout and whole-process RSS are recorded.
`analyze.py` verifies artifact hashes, cardinalities, source/binary identity,
fingerprints and answer counts. `collect_diagnostics.py` records separate profiler
identity. `report.py` verifies per-query work equality and regenerates these tables.

Formatting, all-target Clippy with warnings denied, workspace tests/doctests and
Rustdoc with warnings denied passed. Tests include bit boundaries at 63/64,
growth beyond one word, early target exit, subsequent cuts, scratch reuse on a
smaller graph, full-width IDs and independent matrix-oracle histories for all
13 adapters. Diagnostic fingerprint compatibility covers legacy and sustained
traces. Read-only review found no correctness blocker. Core production source,
Cargo.lock, existing results and staged user changes were preserved.

[Detailed timings, tails and RSS](details.md) and [raw comparison](comparison.json)
show every scenario and its observed process range. Close rankings can reverse
with timing noise; the 10M observations must not be treated as replicated wins.
'''
(HERE/'README.md').write_text(text)
detail='# All epoch/bitset timing cells\n\nBaseline: same-build epoch BFS. Negative delta means lower runtime. Ranges are observed process min/max, not confidence intervals. RSS is whole-process peak.\n\n'
for r in rows:
 detail+=f"## {r['family']} / {r['workload']} / N={r['nodes']} / q={r['query_percent']} / {r['regime']}\n\n"
 detail+='| Engine | Trials | Replay ms [min,max] | Delta | Setup ms | RSS MiB | Cut p95/p99 µs | Link p95/p99 µs | Query p95/p99 µs |\n|---|---:|---|---:|---:|---:|---|---|---|\n'
 for e in E:
  v=r['engines'][e];x=v['metrics'];w=x['runtime_ns']
  def tail(op):return '—' if x[op+'_p95_ns'] is None else f"{x[op+'_p95_ns']['median']/1000:.3f}/{x[op+'_p99_ns']['median']/1000:.3f}"
  detail+=f"| {e} | {v['trials']} | {w['median']/1e6:.3f} [{w['min']/1e6:.3f},{w['max']/1e6:.3f}] | {v['runtime_delta_vs_bfs_percent']:+.2f}% | {x['setup_ns']['median']/1e6:.3f} | {x['rss_bytes']['median']/2**20:.2f} | {tail('cut')} | {tail('link')} | {tail('connected')} |\n"
 detail+='\n'
(HERE/'details.md').write_text(detail)
(HERE/'artifact-sha256.json').write_text(json.dumps({p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(HERE.iterdir()) if p.is_file() and p.name!='artifact-sha256.json'},indent=2)+'\n')
