"""Paired frozen-binary comparison on predeclared reference cells."""
import hashlib,json,random,sys
from pathlib import Path
H=Path(__file__).resolve().parent;ROOT=H.parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from run_baseline import hashes
from run_scale import run_measurement,peak_rss
build=json.loads((H/'builds.json').read_text());assert hashes()==build['original_source_sha256']
assert not (H/'manifest.json').exists()
cases=[]
for family in ('sparse','dense','cogentco'):
 d=ROOT/f'results/2026-10-06-engine-ranking-{family}'
 m=json.loads((d/'manifest.json').read_text())
 for c in m['cases']:
  if c['engine']!='hdt':continue
  if family=='sparse' and c['nodes'] not in (100000,1000000):continue
  if family=='dense' and c['nodes']!=512:continue
  cases.append((family,d,c))
assert len(cases)==114
random.Random(42).shuffle(cases)
meta={'builds':build,'scope':'228 sequential paired runs, alternating order; runtime excludes setup','cases':[]}
for index,(family,d,c) in enumerate(cases):
 ref=json.loads((d/(c['name']+'.json')).read_text())
 for variant in (('before','after') if index%2==0 else ('after','before')):
  b=build['variants'][variant];binary=Path(b['binary']);assert hashlib.sha256(binary.read_bytes()).hexdigest()==b['binary_sha256']
  cmd=['/usr/bin/time','-l',str(binary),*c['command'][3:]]
  name=family+'-'+c['name']+'-'+variant
  result,timeout=run_measurement(cmd,120)
  (H/(name+'.stderr.txt')).write_text(result.stderr)
  (H/(name+('.json' if result.returncode==0 else '.partial-stdout.txt'))).write_text(result.stdout)
  entry={'name':name,'family':family,'variant':variant,'pair':index,'trial':c['trial'],'regime':c['regime'],'reference':str((d/(c['name']+'.json')).relative_to(ROOT)),'command':cmd,'exit_code':result.returncode,'timed_out':timeout,'rss_bytes':peak_rss(result.stderr,sys.platform)}
  meta['cases'].append(entry);(H/'manifest.partial.json').write_text(json.dumps(meta,indent=2)+'\n')
  if result.returncode==0:
   r=json.loads(result.stdout);assert r['trace_fingerprint_fnv1a64']==ref['trace_fingerprint_fnv1a64']
   assert entry['rss_bytes'] is not None
 print(f'{index+1}/114 {c["name"]}',flush=True)
assert hashes()==build['original_source_sha256']
for helper in ('run_baseline.py','run_scale.py'):(H/helper).write_bytes((ROOT/'scripts'/helper).read_bytes())
(H/'manifest.partial.json').unlink()
meta['artifact_sha256']={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(H.iterdir()) if p.is_file()}
(H/'manifest.json').write_text(json.dumps(meta,indent=2)+'\n')
