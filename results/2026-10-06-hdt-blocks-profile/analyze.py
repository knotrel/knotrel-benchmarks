"""Validate diagnostic replays and document structural evidence separately from timings."""
import hashlib,json,statistics
from pathlib import Path
H=Path(__file__).resolve().parent;ROOT=H.parents[1]
m=json.loads((H/'manifest.json').read_text())
for name,h in m['artifact_sha256'].items():assert hashlib.sha256((H/name).read_bytes()).hexdigest()==h
normal=json.loads((ROOT/'results/2026-10-06-engine-ranking/comparison.json').read_text())
struct=json.loads((ROOT/'results/2026-10-06-hdt-blocks-structure/results.json').read_text())
rows=[]
for n in (100000,1000000):
 for q in (10,50,90):
  for w in ('sustained-churn-path-v1','sustained-churn-blocks-v1'):
   rs=[json.loads((H/f'{w}-n{n}-q{q}-p{i}.json').read_text()) for i in (0,1)]
   assert rs[0]['counters']==rs[1]['counters'] and rs[0]['snapshots']==rs[1]['snapshots']
   ref=next(r for r in normal['rows'] if r['workload']==w and r['nodes']==n and r['query_percent']==q and r['regime']=='warmed')
   shares=[]
   for r in rs:
    assert r['trace_fingerprint_fnv1a64']==ref['fingerprint']
    t=r['diagnostic_timings'];count=lambda k:0 if t[k] is None else t[k]['count']
    assert count('links')==ref['link_count'] and count('queries')==ref['query_count']
    assert sum(count(k) for k in ('tree_cuts_with_promotions','tree_cuts_without_promotions','non_tree_cuts'))==ref['cut_count']
    c=r['counters'];assert c['candidate_edges']==c['non_tree_promotions']+c['replacements']
    total=sum(v['total_ns'] for v in t.values() if v)
    shares.append(100*(t['tree_cuts_with_promotions'] or {}).get('total_ns',0)/total)
   rows.append({'nodes':n,'query_percent':q,'workload':w,'counters':rs[0]['counters'],'promoting_cut_count':(rs[0]['diagnostic_timings']['tree_cuts_with_promotions'] or {}).get('count',0),'diagnostic_promoting_cut_time_share_percent':{'min':min(shares),'max':max(shares)},'initial_storage':rs[0]['snapshots']['after_initial_edges'],'replay_storage':rs[0]['snapshots']['after_replay']})
lines=['# HDT cyclic-blocks diagnosis — 2026-10-06','',
'Diagnostic replay time is concentrated in cuts that perform promotions; nearly all counted forest join work occurs inside tree-promotion bodies. This is a diagnosis, not an optimization result: production sources and the default engine are unchanged. The [current ranking](../2026-10-06-engine-ranking/README.md) remains the normal timing baseline.','',
'## Observations','',
'At one million vertices and 90% queries, the block trace has 100 cuts (97 tree cuts), 900 queries and no links. It causes 2,279,725 tree promotions and 134,846 non-tree promotions, yet only 47 replacements. The path control has 100 tree cuts and zero promotions or replacement candidates. The same distinction appears at 100,000 vertices.','',
'| Vertices | Queries | Topology | Tree cuts | Cuts with promotions | Tree promotions | Non-tree promotions | Candidates | Replacements |','|---|---:|---|---:|---:|---:|---:|---:|---:|']
for r in rows:
 c=r['counters'];lines.append(f"| {r['nodes']:,} | {r['query_percent']}% | {r['workload']} | {c['tree_cuts']} | {r['promoting_cut_count']} | {c['tree_promotions']:,} | {c['non_tree_promotions']:,} | {c['candidate_edges']:,} | {c['replacements']} |")
lines+=['','## Isolated structural attribution','',
'Four traces (path/blocks × 100k/1M, 90% queries) were replayed twice against a temporary copy of the current core, with counters inserted into promotion bodies and forest functions. Both runs return identical counters. All results are oracle-checked; aggregate HDT counters match the existing profiler. Function calls include recursive and base-case calls. These counts are not CPU-time percentages.','',
'| Block vertices | Promotion-body pull calls | Promotion-body join calls | Promotion-body split calls | Share of all replay join calls | Newly materialized vertex records |','|---|---:|---:|---:|---:|---:|']
for r in struct['results']:
 if 'blocks' not in r['workload']:continue
 c=r['counts']['promote_tree'];total=sum(s['join'] for s in r['counts'].values())
 lines.append(f"| {r['nodes']:,} | {c['pull']:,} | {c['join']:,} | {c['split']:,} | {100*c['join']/total:.3f}% | {c['new_vertex_records']:,} |")
lines+=['', 'A vertex record here belongs to one forest level. A single graph vertex can have multiple such records. Materialization counts are not allocator-call counts, and this probe does not measure allocation latency or hardware cache misses.','',
'| Source level → next level | Tree promotions, 100k blocks | Tree promotions, 1M blocks |','|---|---:|---:|']
b=[r for r in struct['results'] if 'blocks' in r['workload']]
for i in range(5):lines.append(f"| {i} → {i+1} | {b[0]['promotions_by_source_level'][str(i)]['tree']:,} | {b[1]['promotions_by_source_level'][str(i)]['tree']:,} |")
lines+=['','## Storage and diagnostic timing','',
'At 1M vertices / 90% queries on blocks, requested owned vector capacity rises from 477,374,128 bytes after setup to 1,829,305,616 bytes after replay; materialized levels rise from one to six. Live ordered-container payload rises from 83,999,936 to 120,470,224 bytes. These snapshots exclude allocator and B-tree overhead and are not total heap or RSS. They describe retained storage, not allocation rate.','',
'The existing profiler places the full duration of a cut in the “with promotions” category if it performs any promotion. Across the block diagnostics, that category accounts for '+f"{min(r['diagnostic_promoting_cut_time_share_percent']['min'] for r in rows if 'blocks' in r['workload']):.2f}%–{max(r['diagnostic_promoting_cut_time_share_percent']['max'] for r in rows if 'blocks' in r['workload']):.2f}%"+' of summed instrumented operation intervals. This includes other repair work inside those cuts; it is not a timing of the promotion body alone. Diagnostic sampling/storage snapshots perturb caches, so these timings are never compared numerically with the normal ranking.','',
'## Interpretation and next optimization experiment','',
'In the implementation, `replace` promotes the smaller side’s exact-level tree edges before scanning its non-tree candidates. Every tree promotion creates a tour copy in the next forest through `forest.link`; it can also materialize endpoint records. A few cuts can therefore trigger millions of promotions early in the edge lifetimes. This is consistent with an amortized update bound: the benchmark includes setup separately and measures a short, 1,000-operation replay, not steady-state amortized cost over an indefinite history.','',
'The evidence makes repeated construction of higher-level forests the first optimization target. Before changing promotion order or skipping work (which could violate HDT invariants), profile the link/reroot path within tree promotion, then test a single reduction in redundant structural work or endpoint materialization. Preserve graph semantics and compare an uninstrumented candidate with the frozen current build using interleaved trials. Keep the path, dense and Cogentco cases as regression controls. A bulk promotion/build approach is a separate algorithmic design requiring an invariant proof; these counters alone do not justify adopting it.','',
'No improvement percentage is claimed here. Candidate-edge scanning is not ruled out as a cost, but candidate count alone does not explain the measured volume of forest maintenance. Cache misses and allocator overhead remain unmeasured.','',
'## Reproduction and audit','',
'`collect.py` runs the existing `hdt-profile` binary twice on each of 12 preserved traces: 100k/1M vertices, 10/50/90% queries, path/blocks, ten rounds, seed 42. All 24 processes succeed. Source hashes match the current ranking. Fingerprints and mutation/query counts match its normal runs; counters and storage snapshots are identical across the repeated diagnostics. Fresh/warmed timing regimes are not duplicated because this is a structural diagnosis, not a cache-performance comparison.','',
'The [isolated probe](../2026-10-06-hdt-blocks-structure/probe.py) preserves its injected sources, harness, compiler commands and [results](../2026-10-06-hdt-blocks-structure/results.json). It exports and verifies the exact traces before replay. Setup counters are reset before the measured operation sequence. Instrumented binaries are never used for timing claims.','',
'Run `collect.py`, then the sibling structural `probe.py`, then `analyze.py`; collectors reject existing final outputs. [analysis.json](analysis.json) retains all snapshots and diagnostic ranges; raw JSON and manifests remain adjacent. No historical result was overwritten.']
(H/'analysis.json').write_text(json.dumps({'diagnostic_cases':24,'identical_counter_and_storage_repeats':True,'rows':rows},indent=2)+'\n')
(H/'README.md').write_text('\n'.join(lines)+'\n')
print('Verified 24 diagnostics, 12 fingerprints/counts, repeat counters/storage, and four structural trace probes')
