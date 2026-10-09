"""Report all paired phase counters, without overriding original regression."""
import json,hashlib,statistics
from pathlib import Path
from collections import defaultdict
H=Path(__file__).resolve().parent;m=json.loads((H/'manifest.json').read_text());tb=json.loads((H/'calibration.json').read_text())['mach_timebase'];rows=[];pairs=defaultdict(dict)
for n,d in m['artifact_sha256'].items():assert hashlib.sha256((H/n).read_bytes()).hexdigest()==d,n
for run in m['runs']:
 if run['nodes']!=1000000:continue
 obs=json.loads((H/(run['name']+'-observations.json')).read_text());r=json.loads((H/(run['name']+'.json')).read_text())['repetitions'][0];assert len(obs)==8
 item={'name':run['name'],'variant':run['variant'],'pair':run['pair'],'setup_ns':r['setup_ns'],'runtime_ns':r['workload_wall_ns'],'phases':{}}
 for phase,j,k in [('empty_before',0,1),('setup',2,3),('replay',4,5),('empty_after',6,7)]:
  a,b=obs[j],obs[k];delta={key:b['task'][key]-a['task'][key] for key in ('total_user','total_system','faults','pageins','cow_faults','csw')};assert all(v>=0 for v in delta.values())
  item['phases'][phase]={'counters':delta,'cpu_ns':(delta['total_user']+delta['total_system'])*tb['numer']/tb['denom'],'observer_wall_ns':b['parent_before_ns']-a['parent_before_ns'],'rss_before_bytes':a['task']['resident_size'],'rss_after_bytes':b['task']['resident_size']}
 rows.append(item);pairs[run['pair']][run['variant']]=item
assert len(rows)==16 and len(pairs)==8 and all(set(v)=={'before','after'} for v in pairs.values())
summary={}
for v in ('before','after'):
 rs=[r for r in rows if r['variant']==v];s={}
 values={'runtime_ns':[r['runtime_ns'] for r in rs],'setup_ns':[r['setup_ns'] for r in rs]}
 for phase in ('setup','replay','empty_before','empty_after'):
  for key in ('cpu_ns','observer_wall_ns','rss_before_bytes','rss_after_bytes'):values[phase+'_'+key]=[r['phases'][phase][key] for r in rs]
  for key in ('faults','cow_faults','pageins','csw'):values[phase+'_'+key]=[r['phases'][phase]['counters'][key] for r in rs]
 for key,x in values.items():s[key]={'median':statistics.median(x),'min':min(x),'max':max(x)}
 summary[v]=s
pd=[{'pair':k,'runtime_delta_percent':100*(p['after']['runtime_ns']/p['before']['runtime_ns']-1)} for k,p in sorted(pairs.items())]
change=100*(summary['after']['runtime_ns']['median']/summary['before']['runtime_ns']['median']-1)
(H/'analysis.json').write_text(json.dumps({'rows':rows,'summary':summary,'pairs':pd,'runtime_delta_percent':change,'faster_pairs':sum(p['runtime_delta_percent']<0 for p in pd),'scope':'Separate perturbed diagnostic on exact q50 fresh trace; original regression retained. Resource intervals include marker scheduling; original timer does not.'},indent=2)+'\n')
lines=['# Packed tokens: resource diagnosis on the flagged path','','Exact original flagged trace: one million nodes, 50% query, ten rounds, seed42, no warmup, one replay/process. Eight adjacent pairs with4/4 order balance; two smoke processes. Same phase markers in both variants. [Protocol](protocol.md).','','## Paired timings','',f"Median original workload timer change: **{change:+.2f}%**; packed variant faster in **{sum(p['runtime_delta_percent']<0 for p in pd)}/8** pairs. This is a diagnostic result, not a replacement for the original +119.85% matrix regression.",'','| Variant | Replay ms median (min–max) | Replay CPU ms | Observer replay ms | Setup ms | Replay faults | Replay COW | Replay pageins | Replay switches | RSS after replay MiB |','|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
for v,s in summary.items():
 t=s['runtime_ns'];lines.append(f"| {v} | {t['median']/1e6:.3f} ({t['min']/1e6:.3f}–{t['max']/1e6:.3f}) | {s['replay_cpu_ns']['median']/1e6:.3f} | {s['replay_observer_wall_ns']['median']/1e6:.3f} | {s['setup_ns']['median']/1e6:.3f} | {s['replay_faults']['median']} | {s['replay_cow_faults']['median']} | {s['replay_pageins']['median']} | {s['replay_csw']['median']} | {s['replay_rss_after_bytes']['median']/2**20:.1f} |")
lines+=['','## Every pair','','| Pair | Before ms | After ms | Change | Before/after faults | Before/after COW |','|---:|---:|---:|---:|---|---|']
for d in pd:
 p=pairs[d['pair']];b,a=p['before'],p['after'];bc,ac=b['phases']['replay']['counters'],a['phases']['replay']['counters'];lines.append(f"| {d['pair']} | {b['runtime_ns']/1e6:.3f} | {a['runtime_ns']/1e6:.3f} | {d['runtime_delta_percent']:+.2f}% | {bc['faults']}/{ac['faults']} | {bc['cow_faults']}/{ac['cow_faults']} |")
lines+=['','## Limits','','Markers pause each child to read counters and can change its subsequent scheduling/cache state. Diagnostic code layout also differs from the uninstrumented matrix. CPU time is Mach ticks converted with calibrated timebase; task counters and observer wall include handshake activity, while original setup/replay timers exclude it. Empty brackets are retained and not subtracted. Context switches include handshake switching. Faults are not disk I/O; pageins are separate. Boundary RSS is not peak process RSS, graph payload or allocator allocation count. Sample buffers and teardown are outside the named phases.','','Results cannot establish universal absence of a regression or a causal mechanism. Preserve adverse pairs, the original flagged case and historical results. [analysis.json](analysis.json) retains every phase and range. No page preparation, priority, affinity or system setting was changed. Production sources and candidate patches remain untouched.']
(H/'README.md').write_text('\n'.join(lines)+'\n');print('Runtime change',change,'faster',sum(p['runtime_delta_percent']<0 for p in pd));print(json.dumps(summary,indent=2))
