"""Keep A/A variation and contemporaneous A/B separate; retain every observation."""
import json,hashlib,statistics
from collections import defaultdict
from pathlib import Path
H=Path(__file__).resolve().parent;m=json.loads((H/'manifest.json').read_text());groups=defaultdict(lambda:defaultdict(dict))
for name,digest in m['artifact_sha256'].items():assert hashlib.sha256((H/name).read_bytes()).hexdigest()==digest,name
assert len(m['cases'])==168
failed=[c for c in m['cases'] if c['exit_code']!=0]
for c in m['cases']:
 groups[c['cell'],c['mode']]
 if c['exit_code']!=0:continue
 r=json.loads((H/(c['name']+'.json')).read_text());run=r['repetitions'][0]
 groups[c['cell'],c['mode']][c['trial']][c['label']]={'runtime_ns':run['workload_wall_ns'],'setup_ns':run['setup_ns'],'rss_bytes':c['rss_bytes'],'identity':(r['trace_fingerprint_fnv1a64'],)+tuple(0 if run[k] is None else run[k]['count'] for k in ('query_true','query_false')),'stats':run.get('hdt_stats'),'measurements':run['measurements']}
rows=[]
for (cell,mode),pairs in sorted(groups.items()):
 row={'cell':cell,'mode':mode,'complete':len(pairs)==4 and all(set(p)=={'left','right'} for p in pairs.values())}
 if not row['complete']:rows.append(row);continue
 for p in pairs.values():
  assert p['left']['identity']==p['right']['identity'] and p['left']['stats']==p['right']['stats']
  for op in ('cut','link','connected'):
   a=p['left']['measurements'][op];b=p['right']['measurements'][op]
   assert (a is None and b is None) or a['count']==b['count']
 row['metrics']={}
 for metric in ('runtime_ns','setup_ns','rss_bytes'):
  sides={s:[p[s][metric] for p in pairs.values()] for s in ('left','right')};assert all(v is not None for a in sides.values() for v in a)
  lm,rm=(statistics.median(sides[s]) for s in ('left','right'))
  row['metrics'][metric]={s:{'median':statistics.median(v),'min':min(v),'max':max(v)} for s,v in sides.items()}|{'delta_percent':100*(rm/lm-1)}
 row['pairs']=[{'trial':t,'delta_percent':100*(p['right']['runtime_ns']/p['left']['runtime_ns']-1)} for t,p in sorted(pairs.items())]
 row['faster_pairs']=sum(p['delta_percent']<0 for p in row['pairs']);row['slower_pairs']=sum(p['delta_percent']>0 for p in row['pairs'])
 row['regression_screen']=row['metrics']['runtime_ns']['delta_percent']>5 and row['slower_pairs']>=3
 rows.append(row)
assert len(rows)==21
(H/'comparison.json').write_text(json.dumps({'failed':failed,'rows':rows,'scope':'A/A changes are measurement variability; do not subtract from A/B or pool with previous studies.'},indent=2)+'\n')
lines=['# Promotion-only HDT: A/A regression diagnosis','','Adaptive follow-up on all seven previously flagged cells. Same frozen binaries and traces; four balanced pairs per cell and mode, interleaved in seed42 order. [Protocol](protocol.md). Historical flags remain unchanged; these are not independent randomly selected workloads.','','A/A compares the exact same executable path and SHA-256 on both sides. Negative means right-side median is lower. A/B compares baseline (left) with candidate (right). Percentage is ratio of medians, not median pair change. No outliers removed, no A/A subtraction and no pooling with earlier measurements.','','| Cell | Workload | Nodes | Query % | Regime | Original A/B change |','|---:|---|---:|---:|---|---:|']
for i,r in enumerate(m['selected_cells']):lines.append(f"| {i} | {r['workload']} | {r['nodes']} | {r['query_percent']} | {r['regime']} | {r['metrics']['runtime_ns']['delta_percent']:+.2f}% |")
lines+=['','| Cell | Mode | Left ms | Right ms | Change | Slower pairs | >5% and ≥3 slower |','|---:|---|---:|---:|---:|---:|---|']
for r in rows:
 if not r['complete']:lines.append(f"| {r['cell']} | {r['mode']} | incomplete | — | — | — | — |");continue
 d=r['metrics']['runtime_ns'];lines.append(f"| {r['cell']} | {r['mode']} | {d['left']['median']/1e6:.3f} | {d['right']['median']/1e6:.3f} | {d['delta_percent']:+.2f}% | {r['slower_pairs']}/4 | {'yes' if r['regression_screen'] else 'no'} |")
lines+=['','Four pairs are limited evidence, not an equivalence test. An A/A flag demonstrates that the engineering screen can fire without an algorithm change. It does not prove every A/B regression is noise; lack of an A/A flag does not establish negligible noise. No automatic integration follows.','','Raw operation totals and latency percentiles remain in each process JSON; [comparison.json](comparison.json) includes runtime/setup/RSS ranges and pair changes. Warmed uses a separate untimed graph replay; no hardware-cache flush or answer cache. Workload time excludes setup but includes harness work. RSS is whole-process.','','See [compiled-code inspection](assembly.md) and [audit](audit.json). Production sources and historical results are preserved.']
(H/'README.md').write_text('\n'.join(lines)+'\n')
for r in rows:print(r['cell'],r['mode'],round(r['metrics']['runtime_ns']['delta_percent'],2) if r['complete'] else 'incomplete',r.get('slower_pairs'),r.get('regression_screen'))
