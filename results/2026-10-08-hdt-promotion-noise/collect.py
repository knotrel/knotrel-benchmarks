"""Interleave same-binary controls and A/B confirmation on seven flagged cells."""
import hashlib,json,random,sys
from pathlib import Path
H=Path(__file__).resolve().parent;ROOT=H.parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from run_baseline import hashes
from run_scale import run_measurement,peak_rss
B=H.parent/'2026-10-07-hdt-promotion-joins';M=H.parent/'2026-10-07-hdt-promotion-joins-matrix'
build=json.loads((B/'builds.json').read_text());assert hashes()==build['original_source_sha256']
assert not (H/'manifest.json').exists()
flags=json.loads((M/'assessment.json').read_text())['flagged_cells'];old=json.loads((M/'manifest.json').read_text())
jobs=[]
for index,r in enumerate(flags):
 matches=[]
 for c in old['cases']:
  if c['variant']!='before' or c['trial']!=0:continue
  ref=json.loads((ROOT/c['reference']).read_text())
  key=(ref['workload'],ref.get('config',{}).get('nodes',ref.get('import',{}).get('node_count')),ref.get('query_percent'),c['regime'])
  if key==tuple(r[k] for k in ('workload','nodes','query_percent','regime')):matches.append(c)
 assert len(matches)==1
 for mode in ('AA_before','AA_after','AB'):
  for trial in range(4):jobs.append((index,r,matches[0],mode,trial))
assert len(jobs)==84
random.Random(42).shuffle(jobs)
meta={'builds':build,'protocol':'Interleaved adaptive diagnostic, 7 selected cells x 3 modes x 4 balanced pairs; no pooling with earlier measurements','cases':[],'selected_cells':flags}
for pair,(index,r,ref,mode,trial) in enumerate(jobs):
 for label in (('left','right') if trial%2==0 else ('right','left')):
  variant= ('before' if label=='left' else 'after') if mode=='AB' else mode.removeprefix('AA_')
  b=build['variants'][variant];binary=Path(b['binary']);assert hashlib.sha256(binary.read_bytes()).hexdigest()==b['binary_sha256']
  cmd=['/usr/bin/time','-l',str(binary),*ref['command'][3:]]
  name=f'cell{index}-{mode}-trial{trial}-{label}'
  result,timeout=run_measurement(cmd,120)
  (H/(name+'.stderr.txt')).write_text(result.stderr)
  (H/(name+('.json' if result.returncode==0 else '.partial-stdout.txt'))).write_text(result.stdout)
  entry={'name':name,'cell':index,'mode':mode,'trial':trial,'pair':pair,'label':label,'variant':variant,'reference':ref['reference'],'regime':r['regime'],'command':cmd,'exit_code':result.returncode,'timed_out':timeout,'rss_bytes':peak_rss(result.stderr,sys.platform)}
  meta['cases'].append(entry);(H/'manifest.partial.json').write_text(json.dumps(meta,indent=2)+'\n')
  if result.returncode==0:
   data=json.loads(result.stdout);expected=json.loads((ROOT/ref['reference']).read_text());assert data['trace_fingerprint_fnv1a64']==expected['trace_fingerprint_fnv1a64']
 print(f'{pair+1}/84 cell{index} {mode}',flush=True)
assert hashes()==build['original_source_sha256']
for helper in ('run_baseline.py','run_scale.py'):(H/helper).write_bytes((ROOT/'scripts'/helper).read_bytes())
(H/'manifest.partial.json').unlink()
meta['artifact_sha256']={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(H.iterdir()) if p.is_file()}
(H/'manifest.json').write_text(json.dumps(meta,indent=2)+'\n')
