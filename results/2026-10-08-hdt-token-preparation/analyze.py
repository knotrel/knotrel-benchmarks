"""Compare process-level preparation/replay costs and retain nested counters."""
import hashlib,json,statistics
from pathlib import Path
H=Path(__file__).resolve().parent;m=json.loads((H/'manifest.json').read_text());tb=json.loads((H/'calibration.json').read_text())['mach_timebase']
for n,d in m['artifact_sha256'].items():assert hashlib.sha256((H/n).read_bytes()).hexdigest()==d,n
rows=[];processes=[]
for run in m['runs']:
 if run['nodes']!=1000000:continue
 obs=json.loads((H/(run['name']+'-observations.json')).read_text());report=json.loads((H/(run['name']+'.json')).read_text())
 for i,rep in enumerate(report['repetitions']):
  for phase,j,k in [('empty_before',0,1),('setup',2,3),('preparation',4,5),('replay',6,7),('empty_after',8,9)]:
   a,b=obs[i*10+j],obs[i*10+k];delta={key:b['task'][key]-a['task'][key] for key in ('total_user','total_system','faults','pageins','cow_faults','csw')};assert all(v>=0 for v in delta.values())
   rows.append({'process':run['name'],'mode':run['mode'],'repetition':i,'phase':phase,'counters':delta,'cpu_ns':(delta['total_user']+delta['total_system'])*tb['numer']/tb['denom'],'observer_wall_ns':b['parent_before_ns']-a['parent_before_ns'],'resident_after_bytes':b['task']['resident_size'],'original_ns':rep['setup_ns'] if phase=='setup' else rep['preparation_ns'] if phase=='preparation' else rep['workload_wall_ns'] if phase=='replay' else None})
 reps=report['repetitions'];mean=lambda vs:statistics.mean(vs)
 process={'name':run['name'],'mode':run['mode'],'replays':len(reps),'mean_setup_ns':mean(r['setup_ns'] for r in reps),'mean_preparation_ns':mean(r['preparation_ns'] for r in reps),'mean_replay_ns':mean(r['workload_wall_ns'] for r in reps),'mean_combined_ns':mean(r['preparation_ns']+r['workload_wall_ns'] for r in reps),'replay_min_ns':min(r['workload_wall_ns'] for r in reps),'replay_max_ns':max(r['workload_wall_ns'] for r in reps)}
 for phase in ('preparation','replay'):
  ps=[r for r in rows if r['process']==run['name'] and r['phase']==phase]
  for key in ('faults','cow_faults','pageins','csw'):process[f'{phase}_mean_{key}']=mean(r['counters'][key] for r in ps)
  process[f'{phase}_mean_cpu_ns']=mean(r['cpu_ns'] for r in ps)
 processes.append(process)
summary={}
for mode in ('none','read','write'):
 ps=[p for p in processes if p['mode']==mode];assert len(ps)==3
 summary[mode]={key:{'median':statistics.median(p[key] for p in ps),'min':min(p[key] for p in ps),'max':max(p[key] for p in ps)} for key in ps[0] if key not in ('name','mode')}
for mode,s in summary.items():
 for metric in ('mean_preparation_ns','mean_replay_ns','mean_combined_ns'):
  s[metric]['delta_percent_vs_none']=100*(s[metric]['median']/summary['none'][metric]['median']-1)
(H/'analysis.json').write_text(json.dumps({'rows':rows,'processes':processes,'summary':summary,'scope':'Three process observations per mode; eight internal replays are nested. Resource phases include boundary handshake; original times do not. No causal isolation of cache effects.'},indent=2)+'\n')
lines=['# HDT token-arena preparation diagnostic','','One isolated binary, baseline algorithm, exact path1M,q90 trace. Modes none/read/write run in a balanced three-block order, three processes each, eight fresh-graph replays/process. Each mode also passes a small smoke run. [Protocol](protocol.md).','','## Scope and verification of treatment','','Only initialized forest tokens are touched. For this trace the setup creates 2,999,998 tokens. Each read visits the candidate byte; each write stores its identical black-boxed value. Unused capacity, adjacency trees, maps, graph metadata and sample buffers are not prepared. This is not complete graph/process prefaulting.','','The [saved assembly](touch-assembly.txt) contains a token load at stride 0x60 in the read loop and a token store at the same stride in the write loop. Read mode still writes its black_box temporary on the stack. The state-preservation test compares all Debug-visible forest fields and checks AVL/aggregate invariants after preparation and token recycling; all replay oracle/counters match the reference.','','## Process-level comparison','','Medians below are over three process means, not over 24 independent replays. Preparation+replay is computed per replay before averaging, and excludes setup. All modes share the same diagnostic binary.','','| Mode | Preparation ms | Replay ms | Replay change | Preparation + replay ms | Combined change | Replay faults | Replay COW faults | Preparation faults |','|---|---:|---:|---:|---:|---:|---:|---:|---:|']
for mode,s in summary.items():lines.append(f"| {mode} | {s['mean_preparation_ns']['median']/1e6:.3f} | {s['mean_replay_ns']['median']/1e6:.3f} | {s['mean_replay_ns']['delta_percent_vs_none']:+.2f}% | {s['mean_combined_ns']['median']/1e6:.3f} | {s['mean_combined_ns']['delta_percent_vs_none']:+.2f}% | {s['replay_mean_faults']['median']:.1f} | {s['replay_mean_cow_faults']['median']:.1f} | {s['preparation_mean_faults']['median']:.1f} |")
lines+=['','## Every full-size process','','| Process | Preparation mean ms | Replay mean ms | Replay min–max ms | Combined mean ms | Replay faults mean | Replay COW mean |','|---|---:|---:|---:|---:|---:|---:|']
for p in processes:lines.append(f"| {p['name']} | {p['mean_preparation_ns']/1e6:.3f} | {p['mean_replay_ns']/1e6:.3f} | {p['replay_min_ns']/1e6:.3f}–{p['replay_max_ns']/1e6:.3f} | {p['mean_combined_ns']/1e6:.3f} | {p['replay_mean_faults']:.1f} | {p['replay_mean_cow_faults']:.1f} |")
lines+=['','## Limits','','This is a perturbed resource experiment, not production performance. Touching pages also changes cache state and consumes memory bandwidth. Read versus write helps interpretation but is not perfect causal isolation. Task counters include boundary IPC; original setup/preparation/replay timers exclude it. Empty brackets remain in the raw observations. Page faults are not synonymous with disk I/O; pageins are retained separately. CPU time is converted from Mach ticks using the calibrated system timebase. RSS is sampled at boundaries, not peak graph memory. Sample allocation and graph teardown remain outside these phases.','','No historical measurements are pooled, outliers removed, or latency percentiles combined. [analysis.json](analysis.json) retains individual phases, process observations, range and CPU/resource counters. [Diagnostic patch](diagnostic.patch) and complete source snapshots remain separate from production. No commit or staging action was performed.']
(H/'README.md').write_text('\n'.join(lines)+'\n')
for mode,s in summary.items():print(mode,{k:round(s[k]['median'],3) for k in ('mean_preparation_ns','mean_replay_ns','mean_combined_ns','replay_mean_faults','replay_mean_cow_faults','preparation_mean_faults')})
