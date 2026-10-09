"""Separate perturbed phase counters from original workload timing."""
import hashlib,json,statistics,math
from pathlib import Path
H=Path(__file__).resolve().parent;m=json.loads((H/'manifest.json').read_text());cal=json.loads((H/'calibration.json').read_text());tb=cal['mach_timebase']
for n,d in m['artifact_sha256'].items():assert hashlib.sha256((H/n).read_bytes()).hexdigest()==d,n
rows=[]
for run in m['runs']:
 if run['name']=='smoke':continue
 obs=json.loads((H/(run['name']+'-observations.json')).read_text());report=json.loads((H/(run['name']+'.json')).read_text())
 for i,rep in enumerate(report['repetitions']):
  block=obs[i*8:i*8+8]
  for phase,j,k in [('empty_before',0,1),('setup',2,3),('replay',4,5),('empty_after',6,7)]:
   a,b=block[j],block[k];delta={key:b['task'][key]-a['task'][key] for key in ('total_user','total_system','faults','pageins','cow_faults','csw','syscalls_mach','syscalls_unix')}
   assert all(v>=0 for v in delta.values())
   cpu=(delta['total_user']+delta['total_system'])*tb['numer']/tb['denom'];wall=b['parent_before_ns']-a['parent_before_ns']
   rows.append({'process':run['name'],'repetition':i,'phase':phase,'counter_delta':delta,'cpu_ns':cpu,'observer_wall_ns':wall,'snapshot_cost_start_ns':a['parent_after_ns']-a['parent_before_ns'],'snapshot_cost_end_ns':b['parent_after_ns']-b['parent_before_ns'],'resident_before_bytes':a['task']['resident_size'],'resident_after_bytes':b['task']['resident_size'],'original_interval_ns':rep['workload_wall_ns'] if phase=='replay' else rep['setup_ns'] if phase=='setup' else None})
def summary(v):return {'min':min(v),'median':statistics.median(v),'max':max(v)}
phases={}
for phase in ('setup','replay','empty_before','empty_after'):
 rs=[r for r in rows if r['phase']==phase];phases[phase]={k:summary([r[k] for r in rs]) for k in ('cpu_ns','observer_wall_ns','resident_after_bytes')}
 for k in ('faults','pageins','cow_faults','csw'):phases[phase][k]=summary([r['counter_delta'][k] for r in rs])
 phases[phase]['count']=len(rs)
replays=[r for r in rows if r['phase']=='replay']
def corr(a,b):
 ma,mb=statistics.mean(a),statistics.mean(b);den=math.sqrt(sum((x-ma)**2 for x in a)*sum((x-mb)**2 for x in b))
 return None if den==0 else sum((x-ma)*(y-mb) for x,y in zip(a,b))/den
correlations={k:corr([r['original_interval_ns'] for r in replays],[r['cpu_ns'] if k=='cpu_ns' else r['counter_delta'][k] for r in replays]) for k in ('cpu_ns','faults','pageins','cow_faults','csw')}
out={'rows':rows,'phases':phases,'descriptive_pearson_r':correlations,'scope':'32 nested replays from 4 processes, not independent observations; perturbed boundaries include observer handshake, no causal inference or overhead subtraction.'}
(H/'analysis.json').write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps({'phases':phases,'correlations':correlations},indent=2))
lines=['# HDT scheduling and memory phase diagnosis','','Four baseline-only diagnostic processes, eight path1M,q90 replays each; one small smoke process precedes them. Same algorithm and reference trace, fresh graph each replay. Markers pause the child at phase boundaries while the observer reads macOS task counters. [Protocol](protocol.md).','','## Measurement scope','','These are **perturbed diagnostics**, not comparable performance results. Task CPU time uses Mach ticks on this host: conversion uses mach_timebase_info and was calibrated against getrusage. Native structure size and offsets match the installed SDK. The initial unit-calibration failure is preserved and occurred before child measurements.','','Observer wall and CPU intervals include boundary communication; original workload timers exclude those marker handshakes. Context switches include handshake-induced switching and are not split into voluntary/involuntary. Faults do not necessarily mean disk I/O; pageins are shown separately. Resident bytes are boundary samples, not peak usage or graph payload. Empty brackets estimate observable handshake activity but are not subtracted.','','## Phase summaries','','| Phase | Intervals | Observer wall median ms | CPU median ms | Faults min/median/max | Pageins min/median/max | Context switches min/median/max | RSS median MiB |','|---|---:|---:|---:|---|---|---|---:|']
for phase,s in phases.items():
 fmt=lambda k:'/'.join(str(s[k][v]) for v in ('min','median','max'))
 lines.append(f"| {phase} | {s['count']} | {s['observer_wall_ns']['median']/1e6:.3f} | {s['cpu_ns']['median']/1e6:.3f} | {fmt('faults')} | {fmt('pageins')} | {fmt('csw')} | {s['resident_after_bytes']['median']/2**20:.1f} |")
lines+=['','## Replay observations','','| Process | Replay | Original wall ms | Observed CPU ms | Observer wall ms | Faults | Pageins | Context switches |','|---|---:|---:|---:|---:|---:|---:|---:|']
for r in replays:lines.append(f"| {r['process']} | {r['repetition']} | {r['original_interval_ns']/1e6:.3f} | {r['cpu_ns']/1e6:.3f} | {r['observer_wall_ns']/1e6:.3f} | {r['counter_delta']['faults']} | {r['counter_delta']['pageins']} | {r['counter_delta']['csw']} |")
lines+=['','Descriptive Pearson correlations against original workload wall time: `'+json.dumps(correlations)+'`. These nested observations are not independent; correlations are not causal tests or confidence estimates. Raw boundaries, CPU ticks and snapshot latency remain in [analysis.json](analysis.json) and each observations file.','','The diagnostic adds no unsafe Rust or dependency and does not change production sources. [Patch](diagnostic.patch), source snapshots, compiler/binary hashes and the [calibration](calibration.json) are retained. Instruments was unavailable in the installed Command Line Tools environment. No CPU affinity, priority, cache, swap or system configuration was changed.']
(H/'README.md').write_text('\n'.join(lines)+'\n')
