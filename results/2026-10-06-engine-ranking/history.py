"""Compare matched historical cells, without interpreting drift as causal speedup."""
import hashlib,json,statistics
from collections import Counter
from pathlib import Path
H=Path(__file__).resolve().parent
new=json.loads((H/'comparison.json').read_text())
old=json.loads((H.parent/'2026-10-04-connectivity-campaign/runtime-percentages.json').read_text())
E=['compact-bfs','ett-scan','hdt','petgraph-dfs']
def key(r):return tuple(r[k] for k in ('family','workload','nodes','query_percent','regime'))
current={key(r):r for r in new['rows'] if r['complete']}
identities={}
for f in ('sparse','dense','cogentco'):
 d=H.parent/('2026-10-04-'+f+'-campaign');m=json.loads((d/'manifest.json').read_text())
 for c in m['cases']:
  p=d/(c['name']+'.json');assert hashlib.sha256(p.read_bytes()).hexdigest()==m['artifact_sha256'][p.name]
  r=json.loads(p.read_text());run=r['repetitions'][0]
  k=(f,c.get('workload',r['workload']),c.get('nodes',r.get('import',{}).get('node_count')),c.get('query_percent'),c['regime'])
  identity=(r['trace_fingerprint_fnv1a64'],)+tuple(0 if run[n] is None else run[n]['count'] for n in ('query_true','query_false'))+tuple(0 if run['measurements'][op] is None else run['measurements'][op]['count'] for op in ('cut','link','connected'))
  if k in identities:assert identity==identities[k]
  identities[k]=identity
rows=[]
for r in old['scenarios']:
 if r['family']=='repeats':continue
 n=current.get(key(r))
 if n is None:continue
 assert identities[key(r)]==(n['fingerprint'],n['query_true_count'],n['query_false_count'],n['cut_count'],n['link_count'],n['query_count'])
 times={e:n['engines'][e]['metrics']['runtime_ns']['median'] for e in E};best=min(times.values())
 rows.append({k:r[k] for k in ('family','workload','nodes','query_percent','regime')}|{'old_winners':r['winners'],'current_four_engine_winners':[e for e in E if times[e]==best], 'current_five_engine_winners':n['winners'],'engines':{e:{'old_ns':r['engines'][e]['runtime_ns']['median'],'current_ns':times[e],'drift_percent':100*(times[e]/r['engines'][e]['runtime_ns']['median']-1)} for e in E}})
assert len(identities)==62
out={'matched_complete_cells':len(rows),'historical_cells':62,'identity_checks':'fingerprint, query answers and cut/link/query counts match','interpretation':'Different days/builds/trial counts, not interleaved before/after. Drift is descriptive, not causal.','rows':rows}
(H/'historical-comparison.json').write_text(json.dumps(out,indent=2)+'\n')
a=Counter(e for r in rows for e in r['old_winners']);b=Counter(e for r in rows for e in r['current_four_engine_winners']);c=Counter(e for r in rows for e in r['current_five_engine_winners'])
lines=['# Historical comparison on matched traces','',f"{len(rows)} / 62 original main cells matched by trace fingerprint, actual operation counts and true/false query counts. The twelve one-million-node cells are excluded. Original results remain unchanged.",'','These measurements come from different days and builds and have different trial counts. They show observed drift, not the causal effect of an optimization. Consult the dedicated paired experiments for before/after evidence. The four-engine column holds the competitor set fixed; the five-engine column also admits Workspace.','', '| Engine | Original wins / 62 | Current wins, same four engines | Current wins, with Workspace | Median per-cell runtime drift | Drift min–max |','|---|---:|---:|---:|---:|---:|']
for e in E:
 ds=[r['engines'][e]['drift_percent'] for r in rows]
 lines.append(f'| {e} | {a[e]} | {b[e]} | {c[e]} | {statistics.median(ds):+.1f}% | {min(ds):+.1f}% to {max(ds):+.1f}% |')
lines+= [f"| compact-workspace | not measured | excluded | {c['compact-workspace']} | — | — |",'', 'Drift = `100*(current runtime / historical runtime - 1)`. The median summarizes drift across this selected matrix; it is not an aggregate throughput gain. Per-cell raw medians and percentages are in [historical-comparison.json](historical-comparison.json).']
(H/'historical-comparison.md').write_text('\n'.join(lines)+'\n')
print('\n'.join(lines))
