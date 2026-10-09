"""Treat each process as one sample; validate every rebuilt-graph replay."""
import hashlib,json,statistics,sys
from pathlib import Path
from collections import defaultdict
H=Path(__file__).resolve().parent;D=H/sys.argv[1];m=json.loads((D/'manifest.json').read_text());groups=defaultdict(lambda:defaultdict(dict));orders=defaultdict(lambda:defaultdict(list))
assert len(m['cases'])==24
assert hashlib.sha256((H/'protocol.md').read_bytes()).hexdigest()==m['protocol_sha256']
assert hashlib.sha256((H/'collect.py').read_bytes()).hexdigest()==m['collector_sha256']
for name,digest in m['artifact_sha256'].items():assert hashlib.sha256((D/name).read_bytes()).hexdigest()==digest,name
failed=[c for c in m['cases'] if c['exit_code']!=0];processes=[]
for c in m['cases']:
 orders[c['cell']][c['trial']].append(c['label']);groups[c['cell']]
 if c['exit_code']!=0:continue
 r=json.loads((D/(c['name']+'.json')).read_text());ref=json.loads((H.parents[1]/c['reference']).read_text());expected=ref['repetitions'][0]
 assert len(r['repetitions'])==c['repetitions'] and r['trace_fingerprint_fnv1a64']==ref['trace_fingerprint_fnv1a64']
 for run in r['repetitions']:
  assert run.get('hdt_stats')==expected.get('hdt_stats')
  for field in ('query_true','query_false'):
   assert (0 if run[field] is None else run[field]['count'])==(0 if expected[field] is None else expected[field]['count'])
  for op in ('cut','link','connected'):
   a,b=run['measurements'][op],expected['measurements'][op];assert (a is None and b is None) or a['count']==b['count']
 times=[v['workload_wall_ns'] for v in r['repetitions']];setups=[v['setup_ns'] for v in r['repetitions']]
 values={'mean_replay_ns':sum(times)/len(times),'sum_replay_ns':sum(times),'first_replay_ns':times[0],'median_replay_ns':statistics.median(times),'mean_setup_ns':sum(setups)/len(setups),'rss_bytes':c['rss_bytes']}
 groups[c['cell']][c['trial']][c['label']]=values
 processes.append({'name':c['name'],'cell':c['cell'],'label':c['label'],'trial':c['trial'],'metrics':values,'replay_ns':times,'setup_ns':setups})
rows=[]
for cell,pairs in sorted(groups.items()):
 assert sum(v==['left','right'] for v in orders[cell].values())==2
 assert sum(v==['right','left'] for v in orders[cell].values())==2
 complete=len(pairs)==4 and all(set(p)=={'left','right'} for p in pairs.values());row={'cell':cell,'complete':complete}
 if not complete:rows.append(row);continue
 row['metrics']={}
 for k in next(iter(pairs.values()))['left']:
  sides={s:[p[s][k] for p in pairs.values()] for s in ('left','right')};assert all(v is not None for vs in sides.values() for v in vs)
  a,b=(statistics.median(sides[s]) for s in ('left','right'));row['metrics'][k]={s:{'median':statistics.median(v),'min':min(v),'max':max(v)} for s,v in sides.items()}|{'delta_percent':100*(b/a-1)}
 row['pairs']=[{'trial':t,'delta_percent':100*(p['right']['mean_replay_ns']/p['left']['mean_replay_ns']-1)} for t,p in sorted(pairs.items())]
 row['slower_pairs']=sum(p['delta_percent']>0 for p in row['pairs']);row['regression_screen']=row['metrics']['mean_replay_ns']['delta_percent']>5 and row['slower_pairs']>=3;rows.append(row)
assert len(rows)==3
passed=not failed and all(r['complete'] and abs(r['metrics']['mean_replay_ns']['delta_percent'])<=5 for r in rows)
(D/'assessment.json').write_text(json.dumps({'mode':m['mode'],'failed':failed,'rows':rows,'processes':processes,'screen_passed':passed if m['mode']=='AA' else None,'note':'A/A validation requires absolute process-mean median change <=5% in each cell. Independent observations are four process pairs, not the internal replays.'},indent=2)+'\n')
for r in rows:print(m['mode'],r['cell'],round(r['metrics']['mean_replay_ns']['delta_percent'],2) if r['complete'] else 'incomplete',r.get('slower_pairs'))
print('AA screen:',passed if m['mode']=='AA' else 'not applicable')
