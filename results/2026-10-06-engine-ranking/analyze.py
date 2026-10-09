"""Rank complete same-build cells and retain failed/incomplete observations."""
import hashlib,json,statistics
from collections import defaultdict,Counter
from pathlib import Path
HERE=Path(__file__).resolve().parent
ENGINES=['compact-bfs','compact-workspace','ett-scan','hdt','petgraph-dfs']
EXPECTED={'sparse':720,'dense':360,'cogentco':30,'repeats':60,'extreme':12}
rows=[];failures=[];audits={};binary_hashes=set();sources=[]
for family,expected in EXPECTED.items():
 directory=HERE.parent/('2026-10-06-engine-ranking-'+family)
 m=json.loads((directory/'manifest.json').read_text())
 binary_hashes.add(m['binary_sha256']);sources.append(m['source_sha256'])
 for name,h in m['artifact_sha256'].items():assert hashlib.sha256((directory/name).read_bytes()).hexdigest()==h,(family,name)
 assert len(m['cases'])==expected,(family,len(m['cases']))
 audits[family]={'attempted':expected,'successful':0,'failed':0}
 groups=defaultdict(lambda:defaultdict(list));planned=defaultdict(Counter)
 wanted=ENGINES if family!='extreme' else ['compact-bfs','compact-workspace','petgraph-dfs']
 for c in m['cases']:
  key=(c.get('workload','topology-zoo-outages-v1'),c.get('nodes',197),c.get('query_percent'),c['regime'])
  planned[key][c['engine']]+=1
  if c['exit_code']!=0:
   failures.append(dict(family=family,**c));audits[family]['failed']+=1;continue
  audits[family]['successful']+=1
  r=json.loads((directory/(c['name']+'.json')).read_text());run=r['repetitions'][0]
  assert r['workload']==key[0]
  metrics={'runtime_ns':run['workload_wall_ns'],'setup_ns':run['setup_ns'],'rss_bytes':c['peak_process_rss_bytes']}
  for op,v in list(run['measurements'].items())+[('repeated',run['repeated_queries'])]:
   for field in ['count','total_ns','p50_ns','p95_ns','p99_ns']:metrics[op+'_'+field]=None if v is None else v[field]
  groups[key][c['engine']].append((r,metrics))
 for key,plan in sorted(planned.items()):
  trials=1 if family=='extreme' else 3
  assert set(plan)==set(wanted) and all(n==trials for n in plan.values())
  variants=groups[key]
  complete=set(variants)==set(wanted) and all(len(v)==trials for v in variants.values())
  row=dict(zip(['workload','nodes','query_percent','regime'],key));row.update(family=family,complete=complete,engines={})
  if not variants:row['winner']=None;rows.append(row);continue
  fingerprints={r['trace_fingerprint_fnv1a64'] for vs in variants.values() for r,_ in vs};assert len(fingerprints)==1
  row['fingerprint']=next(iter(fingerprints));first=next(iter(variants.values()))[0][0]
  outcomes=set()
  for values in variants.values():
   for r,metrics in values:
    run=r['repetitions'][0]
    outcomes.add(tuple(0 if run[k] is None else run[k]['count'] for k in ['query_true','query_false'])+tuple(metrics[k+'_count'] or 0 for k in ['cut','link','connected','repeated']))
  assert len(outcomes)==1
  row['query_true_count'],row['query_false_count'],row['cut_count'],row['link_count'],row['query_count'],row['repeat_count']=next(iter(outcomes))
  row.update(initial_edges=first.get('initial_edges'),initial_max_degree=first.get('initial_max_degree'),initial_density=first.get('initial_density'))
  for e,values in variants.items():
   row['engines'][e]={'trials':len(values),'metrics':{}}
   for metric in values[0][1]:
    vs=[v[metric] for _,v in values]
    if all(v is None for v in vs):row['engines'][e]['metrics'][metric]=None;continue
    assert all(v is not None for v in vs)
    row['engines'][e]['metrics'][metric]={'median':statistics.median(vs),'min':min(vs),'max':max(vs)}
   stats=[r['repetitions'][0].get('hdt_stats') for r,_ in values]
   if any(s is not None for s in stats):
    assert all(s==stats[0] for s in stats);row['engines'][e]['hdt_stats']=stats[0]
  if complete:
   times={e:row['engines'][e]['metrics']['runtime_ns']['median'] for e in wanted};best=min(times.values())
   winners=[e for e,v in times.items() if v==best];row['winners']=winners;row['winner']=winners[0] if len(winners)==1 else None
   for e,v in row['engines'].items():
    v['delta_vs_compact_percent']=100*(times[e]/times['compact-bfs']-1)
    v['slower_than_best_percent']=100*(times[e]/best-1)
   winner_range=row['engines'][winners[0]]['metrics']['runtime_ns']
   row['winner_range_separated']=len(winners)==1 and all(winner_range['max']<row['engines'][e]['metrics']['runtime_ns']['min'] for e in wanted if e not in winners)
  else:row['winner']=None
  rows.append(row)
assert len(binary_hashes)==1 and all(s==sources[0] for s in sources)
assert len(rows)==82
main=[r for r in rows if r['family'] in ['sparse','dense','cogentco'] and r['complete']]
counts=Counter(r['winner'] for r in main)
(HERE/'comparison.json').write_text(json.dumps({'baseline':'same-cell Compact median; negative delta means lower runtime; best-engine deltas separately labeled','main_complete_cells':len(main),'main_planned_cells':74,'main_wins':dict(counts),'rows':rows,'failures':failures},indent=2)+'\n')
(HERE/'audit.json').write_text(json.dumps({'collections':audits,'total_attempted':sum(EXPECTED.values()),'failed':len(failures),'same_binary':True,'same_sources':True,'fingerprints_and_operation_counts_match':True},indent=2)+'\n')
print('Main ranking',len(main),dict(counts))
for family in EXPECTED:
 rs=[r for r in rows if r['family']==family and r['complete']];print(family,dict(Counter(r['winner'] for r in rs)))
for n in [1024,10000,100000,1000000]:
 rs=[r for r in rows if r['family']=='sparse' and r['nodes']==n and r['complete']];print(n,dict(Counter(r['winner'] for r in rs)))
