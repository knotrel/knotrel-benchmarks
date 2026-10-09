"""Observe an owned diagnostic process at explicit phase boundaries."""
import ctypes,hashlib,json,os,resource,subprocess,sys,threading,time
from pathlib import Path
from resources import TaskInfo,snapshot,cpu_ns,TIMEBASE
H=Path(__file__).resolve().parent;ROOT=H.parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from run_baseline import hashes
m=json.loads((H/'builds.json').read_text());assert hashes()==m['original_source_sha256'];assert hashlib.sha256(Path(m['binary']).read_bytes()).hexdigest()==m['binary_sha256']
assert not (H/'manifest.json').exists()
abi=subprocess.check_output(['/private/tmp/knotrel-resource-abi'],text=True).strip();assert abi=='96 80 16';assert (ctypes.sizeof(TaskInfo),TaskInfo.csw.offset,TaskInfo.total_user.offset)==(96,80,16)
a=snapshot(os.getpid());r0=resource.getrusage(resource.RUSAGE_SELF);start=time.process_time();x=0
while time.process_time()-start<0.15:x+=1
b=snapshot(os.getpid());r1=resource.getrusage(resource.RUSAGE_SELF);task=cpu_ns(b['total_user']+b['total_system']-a['total_user']-a['total_system']);ru=(r1.ru_utime+r1.ru_stime-r0.ru_utime-r0.ru_stime)*1e9
assert .85<task/ru<1.15
(H/'calibration.json').write_text(json.dumps({'abi':abi,'task_cpu_delta':task,'getrusage_cpu_delta_ns':ru,'ratio':task/ru,'mach_timebase':TIMEBASE,'units_supported':'Raw Mach ticks converted to nanoseconds; calibrated against getrusage within 15%'},indent=2)+'\n')
expected=['empty_before_start','empty_before_end','setup_start','setup_end','replay_start','replay_end','empty_after_start','empty_after_end']
manifest={'build':m,'runs':[],'scope':'Perturbed diagnostic baseline A/A; no inference from nominal labels'}
for name,n,reps in [('smoke',128,2),('pair0-left',1000000,8),('pair0-right',1000000,8),('pair1-right',1000000,8),('pair1-left',1000000,8)]:
 cmd=[m['binary'],'--engine','hdt','--nodes',str(n),'--rounds','10','--seed','42','--query-percent','90','--workload','sustained-churn-path-v1','--warmup','0','--repetitions',str(reps)]
 observations=[];errors=[]
 with (H/(name+'.json')).open('w') as output:
  p=subprocess.Popen(cmd,stdin=subprocess.PIPE,stdout=output,stderr=subprocess.PIPE,text=True,bufsize=1)
  timer=threading.Timer(240,p.kill);timer.start()
  try:
   for line in p.stderr:
    if line.startswith('KNOTREL_PHASE '):
     phase=line.strip().split()[1];assert phase==expected[len(observations)%8],phase
     t0=time.perf_counter_ns();v=snapshot(p.pid);t1=time.perf_counter_ns();observations.append({'phase':phase,'parent_before_ns':t0,'parent_after_ns':t1,'task':v})
     p.stdin.write('ok\n');p.stdin.flush()
    else:errors.append(line)
   code=p.wait();assert code==0,(name,code,errors)
  finally:
   timer.cancel()
   if p.poll() is None:p.kill();p.wait()
   (H/(name+'-observations.json')).write_text(json.dumps(observations,indent=2)+'\n');(H/(name+'.stderr.txt')).write_text(''.join(errors))
 assert len(observations)==reps*8
 r=json.loads((H/(name+'.json')).read_text());assert len(r['repetitions'])==reps
 if n==1000000:
  ref=json.loads((ROOT/'results/2026-10-06-engine-ranking-sparse/sustained-churn-path-v1-n1000000-q90-fresh-p0-hdt.json').read_text());assert r['trace_fingerprint_fnv1a64']==ref['trace_fingerprint_fnv1a64']
  for run in r['repetitions']:
   assert run['hdt_stats']==ref['repetitions'][0]['hdt_stats']
   for op in ('cut','link','connected'):
    a,b=run['measurements'][op],ref['repetitions'][0]['measurements'][op];assert (a is None and b is None) or a['count']==b['count']
 manifest['runs'].append({'name':name,'command':cmd,'nodes':n,'repetitions':reps,'exit_code':code});print(name,'complete',flush=True)
assert hashes()==m['original_source_sha256'];manifest['artifact_sha256']={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(H.iterdir()) if p.is_file()}
(H/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
