"""Report paired ETT changes and matched petgraph results without pooling trials."""
import hashlib,json,statistics
from collections import defaultdict,Counter
from pathlib import Path
H=Path(__file__).resolve().parent;ROOT=H.parents[1]
m=json.loads((H/'manifest.json').read_text())
for n,d in m['artifact_sha256'].items():assert hashlib.sha256((H/n).read_bytes()).hexdigest()==d,n
assert len(m['cases'])==162
G=defaultdict(lambda:defaultdict(dict));orders=defaultdict(list);fail=[]
for c in m['cases']:
 ref=json.loads((ROOT/c['reference']).read_text());key=(c['family'],ref['workload'],ref.get('config',{}).get('nodes',ref.get('import',{}).get('node_count')),ref.get('query_percent'),c['regime'])
 G[key];orders[key].append(c['variant'])
 if c['exit_code']!=0:fail.append(c);continue
 r=json.loads((H/(c['name']+'.json')).read_text());assert r['trace_fingerprint_fnv1a64']==ref['trace_fingerprint_fnv1a64'];assert len(r['repetitions'])==1
 x=r['repetitions'][0];y=ref['repetitions'][0]
 for k in ('query_true','query_false'):assert (x[k] or {}).get('count',0)==(y[k] or {}).get('count',0)
 metrics={'runtime_ns':x['workload_wall_ns'],'setup_ns':x['setup_ns'],'rss_bytes':c['rss_bytes']}
 for k in ('cut','link','connected'):
  assert (x['measurements'][k] or {}).get('count',0)==(y['measurements'][k] or {}).get('count',0)
  for field in ('count','total_ns','p50_ns','p95_ns','p99_ns'):metrics[k+'_'+field]=(x['measurements'][k] or {}).get(field)
 G[key][c['variant']][c['trial']]={'metrics':metrics,'forest_stats':x.get('forest_stats')}
rows=[]
for key,vs in sorted(G.items()):
 row=dict(zip(('family','workload','nodes','query_percent','regime'),key));complete=set(vs)=={'before','after','petgraph'} and all(set(v)==set(range(6)) for v in vs.values());row['complete']=complete
 order=orders[key];assert len(order)==18
 for offset in range(3):assert Counter(order[offset::3])=={'before':2,'after':2,'petgraph':2}
 if complete:
  row['metrics']={}
  for metric in vs['before'][0]['metrics']:
   vals={v:[run['metrics'][metric] for run in rs.values()] for v,rs in vs.items()}
   if all(x is None for a in vals.values() for x in a):continue
   assert all(x is not None for a in vals.values() for x in a)
   summary={v:{'median':statistics.median(a),'min':min(a),'max':max(a)} for v,a in vals.items()}
   b,a,p=(summary[v]['median'] for v in ('before','after','petgraph'))
   row['metrics'][metric]={'variants':summary,'after_vs_before_percent':100*(a/b-1) if b else None,'after_vs_petgraph_percent':100*(a/p-1) if p else None}
  row['pairs']=[{'trial':t,'runtime_change_percent':100*(vs['after'][t]['metrics']['runtime_ns']/vs['before'][t]['metrics']['runtime_ns']-1)} for t in range(6)]
  for pair in row['pairs']:
   t=pair['trial'];pair['metrics']={}
   for metric in row['metrics']:
    b,a,p=(vs[v][t]['metrics'][metric] for v in ('before','after','petgraph'))
    pair['metrics'][metric]={'before':b,'after':a,'petgraph':p,'after_vs_before_percent':100*(a/b-1) if b else None,'after_vs_petgraph_percent':100*(a/p-1) if p else None}
  row['faster_pairs']=sum(p['runtime_change_percent']<0 for p in row['pairs'])
  row['regression_flag']=row['metrics']['runtime_ns']['after_vs_before_percent']>5 and sum(p['runtime_change_percent']>0 for p in row['pairs'])>=4
  row['forest_counters_by_trial']={v:[rs[t]['forest_stats'] for t in range(6)] for v,rs in vs.items()}
 rows.append(row)
assert len(rows)==9
(H/'comparison.json').write_text(json.dumps({'processes':162,'failed':fail,'rows':rows},indent=2)+'\n')
lines=['# ETT direct joins: paired pilot with petgraph','','Only ETT forest link changes: two direct joins replace three concatenations.', 'Production sources remain unchanged. The candidate and baseline reflect the', 'current libraries; historical timing campaigns are not reused as measurements.', '', 'Six trials per engine/cell, all six engine-order permutations, sequential runs.', 'All figures below are per-cell medians. Negative percentages mean less time.', 'RSS is whole-process peak; setup and operation tails remain separate in', '[comparison.json](comparison.json). [Protocol](protocol.md).', '', '| Workload | Nodes | Query % | Regime | Before ms | After ms | Petgraph ms | Change vs before | Change vs petgraph | Faster pairs | RSS change | Setup change | Flag |', '|---|---:|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---|']
for r in rows:
 if not r['complete']:lines.append('Incomplete: '+str(r));continue
 m=r['metrics'];t=m['runtime_ns'];v=t['variants']
 lines.append(f"| {r['workload']} | {r['nodes']} | {r['query_percent']} | {r['regime']} | {v['before']['median']/1e6:.3f} | {v['after']['median']/1e6:.3f} | {v['petgraph']['median']/1e6:.3f} | {t['after_vs_before_percent']:+.2f}% | {t['after_vs_petgraph_percent']:+.2f}% | {r['faster_pairs']}/6 | {m['rss_bytes']['after_vs_before_percent']:+.2f}% | {m['setup_ns']['after_vs_before_percent']:+.2f}% | {r['regression_flag']} |")
lines+=['',f"Failed processes: {len(fail)}. Screening flags: {sum(r.get('regression_flag',False) for r in rows)}.",'','A flag is >5% runtime increase with at least 4/6 adverse pairs, not a significance test.', 'No outliers removed or repeated-until-pass. No hardware-cache flush or answer cache.', 'Fresh/warmed refer to deliberate full-graph replay warmup. Fixed operation counts', 'change the mutated fraction at different sizes. Cogentco is one real topology', 'with synthetic outages; no general market superiority or tail guarantee follows.', '', 'Tests, source/binary provenance and the saved patch accompany this report.', 'Existing forest differential/invariant tests ran on both variants. The full', 'candidate workspace checks are in [verification.json](verification.json).']
(H/'README.md').write_text('\n'.join(lines)+'\n')
for r in rows:
 if r['complete']:print(r['workload'],r['nodes'],r['regime'],round(r['metrics']['runtime_ns']['after_vs_before_percent'],2),r['faster_pairs'],r['regression_flag'])
