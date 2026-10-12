"""Audit exact outcomes and report all paired results without removing outliers."""
import hashlib,json,re,statistics
from collections import defaultdict
from pathlib import Path
H=Path(__file__).resolve().parent;ROOT=H.parents[1]
m=json.loads((H/'manifest.json').read_text())
for n,d in m['artifact_sha256'].items():assert hashlib.sha256((H/n).read_bytes()).hexdigest()==d,n
assert len(m['cases'])==72
structure={}
for v in ('before','after'):
 a,b=[json.loads((H/f'structure-{v}-{i}.json').read_text()) for i in range(2)]
 assert a==b
 structure[v]=a
assert structure['before']==structure['after'], 'Structural replay differs'
struct_summary={op:{'root_calls':sum(x['phases'][0][0] for x in structure['before']['operations'] if x['operation']==op),'root_steps':sum(x['phases'][0][1] for x in structure['before']['operations'] if x['operation']==op)} for op in ('cut','connected')}
G=defaultdict(lambda:defaultdict(dict));fail=[]
for c in m['cases']:
 G[c['reference']]
 if c['exit_code']!=0:fail.append(c);continue
 r=json.loads((H/(c['name']+'.json')).read_text());ref=json.loads((ROOT/c['reference']).read_text())
 assert r['trace_fingerprint_fnv1a64']==ref['trace_fingerprint_fnv1a64']
 x=r['repetitions'][0];y=ref['repetitions'][0]
 for k in ('query_true','query_false'):assert (x[k] or {}).get('count',0)==(y[k] or {}).get('count',0)
 metrics={'runtime_ns':x['workload_wall_ns'],'setup_ns':x['setup_ns']}
 for op in ('cut','link','connected'):
  assert (x['measurements'][op] or {}).get('count',0)==(y['measurements'][op] or {}).get('count',0)
  if x['measurements'][op]:
   for field in ('total_ns','p50_ns','p95_ns','p99_ns'):metrics[op+'_'+field]=x['measurements'][op][field]
 stderr=(H/(c['name']+'.stderr.txt')).read_text()
 t=re.search(r'([\d.]+) real\s+([\d.]+) user\s+([\d.]+) sys',stderr)
 assert t
 for key,value in zip(('process_real_s','process_user_s','process_sys_s'),t.groups()):metrics[key]=float(value)
 for line in stderr.splitlines():
  match=re.fullmatch(r'\s*(\d+)\s+(.+)',line)
  if match:metrics['process_'+match[2].replace(' ','_')]=int(match[1])
 G[c['reference']][c['trial']][c['variant']]={'metrics':metrics,'stats':x['forest_stats']}
rows=[]
for ref,trials in sorted(G.items()):
 row={'reference':ref,'complete':len(trials)==12 and all(set(v)=={'before','after'} for v in trials.values())}
 if row['complete']:
  pairs=[]
  for trial,vs in sorted(trials.items()):
   assert vs['before']['stats']==vs['after']['stats']
   pairs.append({'trial':trial,'values':{v:x['metrics'] for v,x in vs.items()},'runtime_change_percent':100*(vs['after']['metrics']['runtime_ns']/vs['before']['metrics']['runtime_ns']-1)})
  row['pairs']=pairs;row['metrics']={}
  for key in pairs[0]['values']['before']:
   vals={v:[p['values'][v][key] for p in pairs] for v in ('before','after')}
   med={v:statistics.median(x) for v,x in vals.items()}
   row['metrics'][key]={'median':med,'range':{v:[min(x),max(x)] for v,x in vals.items()},'change_percent':100*(med['after']/med['before']-1) if med['before'] else None}
  row['faster_pairs']=sum(p['runtime_change_percent']<0 for p in pairs)
  row['flag']=row['metrics']['runtime_ns']['change_percent']>5 and row['faster_pairs']<=4
  row['stats']=trials[0]['before']['stats']
 rows.append(row)
assert len(rows)==3
for ref in G:
 groups=[m['cases'][i:i+2] for i in range(0,72,2) if m['cases'][i]['reference']==ref]
 assert len(groups)==12
 assert sum(g[0]['variant']=='before' for g in groups)==6
 for g in groups:assert len({c['trial'] for c in g})==1 and {c['variant'] for c in g}=={'before','after'}
out={'processes':72,'failed':fail,'structural_exact_match':True,'structural_counters':struct_summary,'rows':rows}
(H/'comparison.json').write_text(json.dumps(out,indent=2)+'\n')
for r in rows:
 print(r['reference'],r['complete'])
 if r['complete']:
  print('change',r['metrics']['runtime_ns']['change_percent'],'faster',r['faster_pairs'],'flag',r['flag'])
  print('pairs',[round(p['runtime_change_percent'],2) for p in r['pairs']])
print('structural',struct_summary)
