"""Compare paired uninstrumented variants; preserve every observed regression."""
import hashlib,json,statistics
from collections import defaultdict
from pathlib import Path
H=Path(__file__).resolve().parent
m=json.loads((H/'manifest.json').read_text())
for name,digest in m['artifact_sha256'].items():assert hashlib.sha256((H/name).read_bytes()).hexdigest()==digest,name
assert len(m['cases'])==304
failed=[c for c in m['cases'] if c['exit_code']!=0]
groups=defaultdict(lambda:defaultdict(dict));identities=defaultdict(set)
for c in m['cases']:
 if c['exit_code']!=0:
  ref=json.loads((H.parents[1]/c['reference']).read_text())
  key=(c['family'],ref['workload'],ref.get('config',{}).get('nodes',ref.get('import',{}).get('node_count')),ref.get('query_percent'),c['regime'])
  groups[key]
  continue
 r=json.loads((H/(c['name']+'.json')).read_text());run=r['repetitions'][0]
 key=(c['family'],r['workload'],r.get('config',{}).get('nodes',r.get('import',{}).get('node_count')),r.get('query_percent'),c['regime'])
 metrics={'runtime_ns':run['workload_wall_ns'],'setup_ns':run['setup_ns'],'rss_bytes':c['rss_bytes']}
 for op in ('cut','link','connected'):
  for field in ('count','total_ns','p50_ns','p95_ns','p99_ns'):metrics[op+'_'+field]=None if run['measurements'][op] is None else run['measurements'][op][field]
 identities[key].add((r['trace_fingerprint_fnv1a64'],)+tuple(0 if run[k] is None else run[k]['count'] for k in ('query_true','query_false'))+tuple(metrics[k+'_count'] or 0 for k in ('cut','link','connected')))
 groups[key][c['variant']][c['pair']]={'metrics':metrics,'stats':run.get('hdt_stats')}
rows=[]
for key,vs in sorted(groups.items()):
 assert len(identities[key])<=1
 complete=set(vs)=={'before','after'} and len(vs['before'])==len(vs['after'])==4 and set(vs['before'])==set(vs['after'])
 row=dict(zip(('family','workload','nodes','query_percent','regime'),key));row.update(complete=complete)
 if not complete:rows.append(row);continue
 for pair in vs['before']:assert vs['before'][pair]['stats']==vs['after'][pair]['stats']
 row['metrics']={}
 for metric in next(iter(vs['before'].values()))['metrics']:
  vals={v:[s['metrics'][metric] for s in data.values()] for v,data in vs.items()}
  if all(x is None for a in vals.values() for x in a):row['metrics'][metric]=None;continue
  assert all(x is not None for a in vals.values() for x in a)
  b,a=statistics.median(vals['before']),statistics.median(vals['after'])
  row['metrics'][metric]={'before':{'median':b,'min':min(vals['before']),'max':max(vals['before'])},'after':{'median':a,'min':min(vals['after']),'max':max(vals['after'])},'delta_percent':None if b==0 else 100*(a/b-1)}
 row['pairs']=[{'pair':p,'runtime_delta_percent':100*(vs['after'][p]['metrics']['runtime_ns']/vs['before'][p]['metrics']['runtime_ns']-1)} for p in vs['before']]
 row['pairs_faster']=sum(p['runtime_delta_percent']<0 for p in row['pairs'])
 rows.append(row)
assert len(rows)==38
out={'planned_processes':304,'failed':failed,'rows':rows,'scope':'Median wall runtime, negative change means improvement; no pooled throughput or causal claim for noisy individual cells.'}
(H/'comparison.json').write_text(json.dumps(out,indent=2)+'\n')
for family in ('sparse','dense','cogentco'):
 rs=[r for r in rows if r['family']==family and r['complete']];ds=[r['metrics']['runtime_ns']['delta_percent'] for r in rs]
 if not ds:
  print(family,'no complete cells');continue
 print(family,len(rs),'faster',sum(v<0 for v in ds),'median',statistics.median(ds),'range',min(ds),max(ds))
for r in rows:
 if r['complete'] and r['family']=='sparse':print(r['nodes'],r['workload'],r['query_percent'],r['regime'],round(r['metrics']['runtime_ns']['delta_percent'],2),r['pairs_faster'])
