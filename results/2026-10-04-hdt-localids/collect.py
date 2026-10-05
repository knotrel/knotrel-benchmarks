"""Re-run all HDT reference cells on two pinned release binaries, paired/alternating.
Usage from repository root: python3 RESULTS/collect.py
Build snapshots and binaries must exist in /private/tmp/knotrel-hdt-localids.
"""
import hashlib,json,random,sys,shutil,platform
from pathlib import Path
sys.path.insert(0,str(Path.cwd()/'scripts'))
from run_baseline import ROOT,CORE,hashes,source_patch,command
from run_scale import peak_rss,run_measurement
OUT=Path(__file__).resolve().parent
LOCAL=Path('/private/tmp/knotrel-hdt-localids')
assert not (OUT/'manifest.json').exists() and not (OUT/'manifest.partial.json').exists(), 'use a fresh output collection'
meta={'scope':'Paired frozen before/after release binaries; only HDT candidate measured; reference engines unchanged.',
      'variants':{v:json.loads((LOCAL/(v+'.json')).read_text()) for v in ['before','after']},
      'platform':platform.platform(),'compiler':command(['rustc','-vV']),
      'memory_scope':'Peak whole process including trace, setup, validation and warmup, not engine-only RSS.',
      'cases':[]}
(OUT/'core-after.patch').write_text(source_patch(CORE)+'\n')
for name in ['run_scale.py','run_baseline.py']:(OUT/name).write_bytes((ROOT/'scripts'/name).read_bytes())
cases=[]
for family in ['sparse','dense','repeats','cogentco']:
 d=ROOT/f'results/2026-10-04-{family}-campaign'
 m=json.loads((d/'manifest.json').read_text())
 for c in m['cases']:
  if c['engine']=='hdt':cases.append((family,c,d))
random.Random(42).shuffle(cases)
for i,(family,source,directory) in enumerate(cases):
 reference=json.loads((directory/(source['name']+'.json')).read_text())
 # Reference time wrapper has exactly two leading args; replace only binary/export path.
 base=source['command'][3:]
 for variant in (['before','after'] if i%2==0 else ['after','before']):
  name=family+'-'+source['name']+'-'+variant
  args=list(base)
  if '--trace-out' in args:
   args[args.index('--trace-out')+1]=str(OUT/(name+'.trace.json'))
  if '--trace-in' in args:
   args[args.index('--trace-in')+1]='/private/tmp/knotrel-topology-zoo-20261004/cogentco.trace.json'
  binary=LOCAL/variant
  assert hashlib.sha256(binary.read_bytes()).hexdigest()==meta['variants'][variant]['binary_sha256']
  invocation=['/usr/bin/time','-l' if sys.platform=='darwin' else '-v',str(binary),*args]
  result,timeout=run_measurement(invocation,120)
  (OUT/(name+'.stderr.txt')).write_text(result.stderr)
  (OUT/(name+'.json')).write_text(result.stdout)
  case={k:source[k] for k in ['trial','regime','engine']}
  case.update({'name':name,'family':family,'variant':variant,'reference':str((directory/(source['name']+'.json')).relative_to(ROOT)), 'command':invocation,'exit_code':result.returncode,'timed_out':timeout,'peak_process_rss_bytes':peak_rss(result.stderr,sys.platform)})
  meta['cases'].append(case)
  (OUT/'manifest.partial.json').write_text(json.dumps(meta,indent=2)+'\n')
  result.check_returncode();report=json.loads(result.stdout)
  assert report['trace_fingerprint_fnv1a64']==reference['trace_fingerprint_fnv1a64']
  assert report['repetitions'][0]['hdt_stats']==reference['repetitions'][0]['hdt_stats']
  assert case['peak_process_rss_bytes'] is not None
 print(f'{i+1}/{len(cases)} {family} {source["name"]}',flush=True)
assert hashes()==meta['variants']['after']['source_sha256'],'source changed during collection'
(OUT/'manifest.partial.json').unlink()
meta['artifact_sha256']={str(p.relative_to(OUT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(OUT.rglob('*')) if p.is_file()}
(OUT/'manifest.json').write_text(json.dumps(meta,indent=2)+'\n')
