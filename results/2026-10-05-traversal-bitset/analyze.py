"""Compare exact cells; keep scale and single-trial exploration separate."""
import hashlib,json,statistics
from collections import defaultdict,Counter
from pathlib import Path
HERE=Path(__file__).resolve().parent
ENGINES=['traversal-bfs','traversal-bitset','compact-workspace','petgraph-dfs']
rows=[];audits={};failures=[];binary_hashes=set();sources=[]
for family in ['sparse','dense','extreme','cogentco']:
 directory=HERE.parent/('2026-10-05-traversal-bitset-'+family)
 m=json.loads((directory/'manifest.json').read_text());binary_hashes.add(m['binary_sha256']);sources.append(m['source_sha256'])
 for name,h in m['artifact_sha256'].items():assert hashlib.sha256((directory/name).read_bytes()).hexdigest()==h,(family,name)
 audits[family]=len(m['cases']);assert audits[family]=={'sparse':576,'dense':288,'extreme':16,'cogentco':24}[family]
 groups=defaultdict(lambda:defaultdict(list))
 for c in m['cases']:
  if c['exit_code']!=0:failures.append(dict(family=family,**c));continue
  r=json.loads((directory/(c['name']+'.json')).read_text());run=r['repetitions'][0]
  n=c.get('nodes',r.get('import',{}).get('node_count'));key=(r['workload'],n,r.get('query_percent'),c['regime'])
  metrics={'runtime_ns':run['workload_wall_ns'],'setup_ns':run['setup_ns'],'rss_bytes':c['peak_process_rss_bytes']}
  for op,v in run['measurements'].items():
   for field in ['count','total_ns','p50_ns','p95_ns','p99_ns']:metrics[op+'_'+field]=None if v is None else v[field]
  groups[key][c['engine']].append((r,metrics))
 for key,variants in sorted(groups.items()):
  assert set(variants)==set(ENGINES),'incomplete cell; do not rank'
  assert all(len(v)==(1 if family=='extreme' else 3) for v in variants.values()),'incomplete trials; do not rank'
  fingerprints={r['trace_fingerprint_fnv1a64'] for vs in variants.values() for r,_ in vs};assert len(fingerprints)==1
  first=next(iter(variants.values()))[0][0]
  outcomes={(r['repetitions'][0]['query_true']['count'] if r['repetitions'][0]['query_true'] else 0, r['repetitions'][0]['query_false']['count'] if r['repetitions'][0]['query_false'] else 0) for vs in variants.values() for r,_ in vs}
  assert len(outcomes)==1
  row=dict(zip(['workload','nodes','query_percent','regime'],key));row.update(family=family,fingerprint=next(iter(fingerprints)),engines={})
  for e,values in variants.items():
   row['engines'][e]={'trials':len(values),'metrics':{}}
   for metric in values[0][1]:
    vs=[v[metric] for _,v in values]
    if all(v is None for v in vs):
     row['engines'][e]['metrics'][metric]=None;continue
    assert all(v is not None for v in vs)
    row['engines'][e]['metrics'][metric]={'median':statistics.median(vs),'min':min(vs),'max':max(vs)}
  baseline=row['engines']['traversal-bfs']['metrics']['runtime_ns']['median']
  for e,v in row['engines'].items():v['runtime_delta_vs_bfs_percent']=100*(v['metrics']['runtime_ns']['median']/baseline-1)
  row['winner']=min(ENGINES,key=lambda e:row['engines'][e]['metrics']['runtime_ns']['median'])
  row['query_true_count'],row['query_false_count']=next(iter(outcomes))
  row['initial_edges']=first.get('initial_edges');row['initial_max_degree']=first.get('initial_max_degree');row['initial_density']=first.get('initial_density')
  rows.append(row)
assert len(binary_hashes)==1 and all(s==sources[0] for s in sources)
(HERE/'comparison.json').write_text(json.dumps({'baseline':'traversal-bfs in each cell; negative delta is lower runtime','rows':rows,'failures':failures},indent=2)+'\n')
(HERE/'audit.json').write_text(json.dumps({'processes':audits,'total':sum(audits.values()),'failures':len(failures),'same_binary':True,'same_sources':True,'fingerprints_match_per_cell':True},indent=2)+'\n')
for n in sorted({r['nodes'] for r in rows if r['family']=='sparse'}):
 rs=[r for r in rows if r['family']=='sparse' and r['nodes']==n];print(n,dict(Counter(r['winner'] for r in rs)))
for r in rows:
 if r['regime']=='warmed' and (r['query_percent']==50 or r['family']=='cogentco'):
  print(r['family'],r['nodes'],r['workload'],{e:round(v['runtime_delta_vs_bfs_percent'],1) for e,v in r['engines'].items()})
