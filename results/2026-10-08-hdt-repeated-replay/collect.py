"""Use existing repetitions, fresh graph per replay; keep process-level inference."""
import hashlib,json,random,sys
from pathlib import Path
H=Path(__file__).resolve().parent;ROOT=H.parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from run_baseline import hashes
from run_scale import run_measurement,peak_rss
mode=sys.argv[1];assert mode in ('AA','AB');D=H/mode;D.mkdir(exist_ok=True);assert not (D/'manifest.json').exists()
if mode=='AB':assert json.loads((H/'AA/assessment.json').read_text())['screen_passed'],'A/A validation did not pass; no automatic A/B'
build=json.loads((H.parent/'2026-10-07-hdt-promotion-joins/builds.json').read_text());assert hashes()==build['original_source_sha256']
m=json.loads((H.parent/'2026-10-07-hdt-promotion-joins-matrix/manifest.json').read_text())
selection=[('sustained-churn-path-v1',100000,50,'warmed',16),('sustained-churn-path-v1',1000000,90,'fresh',16),('sustained-churn-blocks-v1',1000000,90,'warmed',2)]
jobs=[]
for cell,(workload,n,q,regime,reps) in enumerate(selection):
 matched=[]
 for c in m['cases']:
  if c['variant']!='before' or c['trial']!=0:continue
  r=json.loads((ROOT/c['reference']).read_text())
  if (r['workload'],r.get('config',{}).get('nodes'),r.get('query_percent'),c['regime'])==(workload,n,q,regime):matched.append(c)
 assert len(matched)==1
 for trial in range(4):jobs.append((cell,matched[0],reps,trial))
random.Random(42).shuffle(jobs)
meta={'mode':mode,'builds':build,'selection':selection,'cases':[],'process_level_statistic':'sum of repetition workload_wall_ns divided by repetition count; setup excluded'}
for pair,(cell,c,reps,trial) in enumerate(jobs):
 for label in (('left','right') if trial%2==0 else ('right','left')):
  variant='after' if mode=='AB' and label=='right' else 'before'
  b=build['variants'][variant];assert hashlib.sha256(Path(b['binary']).read_bytes()).hexdigest()==b['binary_sha256']
  cmd=['/usr/bin/time','-l',b['binary'],*c['command'][3:]];cmd[cmd.index('--repetitions')+1]=str(reps)
  result,timeout=run_measurement(cmd,300);name=f'cell{cell}-trial{trial}-{label}'
  (D/(name+'.stderr.txt')).write_text(result.stderr);(D/(name+('.json' if result.returncode==0 else '.partial-stdout.txt'))).write_text(result.stdout)
  entry={'name':name,'cell':cell,'trial':trial,'pair':pair,'label':label,'variant':variant,'repetitions':reps,'reference':c['reference'],'command':cmd,'exit_code':result.returncode,'timed_out':timeout,'rss_bytes':peak_rss(result.stderr,sys.platform)}
  meta['cases'].append(entry);(D/'manifest.partial.json').write_text(json.dumps(meta,indent=2)+'\n')
  if result.returncode==0:
   r=json.loads(result.stdout);ref=json.loads((ROOT/c['reference']).read_text());assert r['trace_fingerprint_fnv1a64']==ref['trace_fingerprint_fnv1a64'];assert len(r['repetitions'])==reps
 print(f'{mode} {pair+1}/12 cell{cell}',flush=True)
assert hashes()==build['original_source_sha256']
(D/'manifest.partial.json').unlink();meta['artifact_sha256']={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(D.iterdir()) if p.is_file()}
meta['protocol_sha256']=hashlib.sha256((H/'protocol.md').read_bytes()).hexdigest();meta['collector_sha256']=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
(D/'manifest.json').write_text(json.dumps(meta,indent=2)+'\n')
