"""Compare deterministic per-cut work; structural counts are not CPU shares."""
import json,hashlib,sys
from pathlib import Path
H=Path(__file__).resolve().parent;ROOT=H.parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from run_baseline import hashes
m=json.loads((H/'manifest.json').read_text());assert hashes()==m['builds']['original_source_sha256'];assert len(m['runs'])==12
for n,d in m['artifact_sha256'].items():assert hashlib.sha256((H/n).read_bytes()).hexdigest()==d,n
by={}
for run in m['runs']:
 assert run['exit_code']==0
 x=json.loads((H/(run['name']+'.json')).read_text());key=(run['workload'],run['variant'])
 if key in by:assert by[key]==x
 by[key]=x
results=[]
for workload in sorted({k[0] for k in by}):
 b,a=(by[(workload,v)] for v in ('before','after'))
 assert b['trace_fingerprint_fnv1a64']==a['trace_fingerprint_fnv1a64']
 assert [(o['index'],o['operation'],o['answer']) for o in b['operations']]==[(o['index'],o['operation'],o['answer']) for o in a['operations']]
 family='dense' if 'bridge-churn' in workload else 'sparse'
 refpath=ROOT/f'results/2026-10-06-engine-ranking-{family}'/f'{workload}-n{b["nodes"]}-q{b["query_percent"]}-warmed-p0-ett-scan.json'
 ref=json.loads(refpath.read_text());assert b['trace_fingerprint_fnv1a64']==ref['trace_fingerprint_fnv1a64']
 result={'workload':workload,'nodes':b['nodes'],'query_percent':b['query_percent'],'variants':{},'reference':str(refpath.relative_to(ROOT))}
 for variant,x in [('before',b),('after',a)]:
  groups={}
  for o in x['operations']:
   group=o['operation']
   if group=='cut':group='tree_cut' if o['forest_stats_delta'][0] else 'non_tree_cut'
   g=groups.setdefault(group,{'count':0,'phases':[[0]*10 for _ in range(4)],'forest_stats':[0]*4})
   g['count']+=1
   for p in range(4):
    for c in range(10):g['phases'][p][c]+=o['phases'][p][c]
   for i in range(4):g['forest_stats'][i]+=o['forest_stats_delta'][i]
  result['variants'][variant]=groups
 results.append(result)
(H/'analysis.json').write_text(json.dumps({'results':results,'phases':b['phases'],'columns':b['columns'],'repeatability':'Both repeats byte-equivalent JSON for each variant/workload','scope':'Counters only, no timings or CPU shares'},indent=2)+'\n')
lines=['# ETT cut structural diagnosis','','Identical instrumentation in the baseline and direct-join candidate. Each of', 'three traces replayed twice per variant in fresh processes: 12 successful runs.', 'Repeated outputs match exactly. Production source hashes remain unchanged.', 'Oracle answers and historical trace fingerprints match. No elapsed times are measured.', '', '| Workload | Phase | Counter | Before | After | Change |','|---|---|---|---:|---:|---:|']
for r in results:
 before=r['variants']['before'].get('tree_cut');after=r['variants']['after'].get('tree_cut')
 if not before:continue
 for pi,phase in enumerate(b['phases']):
  for ci,counter in enumerate(b['columns']):
   bv,av=before['phases'][pi][ci],after['phases'][pi][ci]
   if bv or av:lines.append(f"| {r['workload']} | {phase} | {counter} | {bv} | {av} | {100*(av/bv-1):+.2f}% |" if bv else f"| {r['workload']} | {phase} | {counter} | {bv} | {av} | new work |")
lines+=['','Counts above sum tree-cut operations only. Split/join counts include recursive', 'and base-case calls; root/rank steps count parent edges actually followed.', 'Candidate tokens count iterator stack pops, including non-yielded structural tokens.', 'Other includes endpoint and candidate-mark work outside the three named phases.', 'Counter increments perturb execution but not token layout. Count changes do not', 'quantify time shares or establish cache/scheduling causality. Original uninstrumented', '[timing observations](../2026-10-10-ett-direct-joins/README.md) remain separate.', '', '[Full analysis](analysis.json) retains all operation groups; raw files retain', 'per-operation counters. [Protocol](protocol.md), [builds](builds.json),', '[verification](verification.json). No production changes, staging or commits.']
(H/'README.md').write_text('\n'.join(lines)+'\n')
print('Repeatability, source hashes, references and answers passed')
for r in results:
 print(r['workload'])
 for v in ('before','after'):print(v,r['variants'][v].get('tree_cut'))
