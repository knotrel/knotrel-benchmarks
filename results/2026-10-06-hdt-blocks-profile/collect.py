"""Collect existing HDT diagnostics against the preserved current ranking."""
import hashlib,itertools,json,subprocess,sys
from pathlib import Path
H=Path(__file__).resolve().parent
ROOT=H.parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from run_baseline import hashes
from run_scale import run_measurement
reference=ROOT/'results/2026-10-06-engine-ranking-sparse/manifest.json'
base=json.loads(reference.read_text());before=hashes()
assert before==base['source_sha256']
assert not (H/'manifest.json').exists(), 'Do not overwrite existing collection'
build=['cargo','build','--release','--locked','--bin','hdt-profile']
subprocess.run(build,cwd=ROOT,check=True)
binary=ROOT/'target/release/hdt-profile'
meta={'reference':str(reference.relative_to(ROOT)),'reference_sha256':hashlib.sha256(reference.read_bytes()).hexdigest(),'source_sha256':before,'binary_sha256':hashlib.sha256(binary.read_bytes()).hexdigest(),'build_command':build,'scope':'Diagnostic timings are perturbed; not comparable with normal runtime. Storage capacities exclude allocator/B-tree overhead.','cases':[]}
for n,q,w in itertools.product([100000,1000000],[10,50,90],['sustained-churn-path-v1','sustained-churn-blocks-v1']):
 name=f'{w}-n{n}-q{q}'
 cmd=[str(binary),'--engine','hdt','--nodes',str(n),'--rounds','10','--seed','42','--query-percent',str(q),'--workload',w]
 for trial in range(2):
  label=name+f'-p{trial}';result,timeout=run_measurement(cmd,180)
  (H/(label+'.json')).write_text(result.stdout);(H/(label+'.stderr.txt')).write_text(result.stderr)
  meta['cases'].append({'name':label,'nodes':n,'query_percent':q,'workload':w,'trial':trial,'command':cmd,'exit_code':result.returncode,'timed_out':timeout})
  (H/'manifest.partial.json').write_text(json.dumps(meta,indent=2)+'\n')
  result.check_returncode();r=json.loads(result.stdout)
  ref=next(c for c in base['cases'] if c['nodes']==n and c['query_percent']==q and c['workload']==w and c['engine']=='hdt')
  normal=json.loads((reference.parent/(ref['name']+'.json')).read_text())
  assert r['trace_fingerprint_fnv1a64']==normal['trace_fingerprint_fnv1a64']
  print(label,flush=True)
assert hashes()==before
for helper in ('run_baseline.py','run_scale.py'):(H/helper).write_bytes((ROOT/'scripts'/helper).read_bytes())
(H/'manifest.partial.json').unlink()
meta['artifact_sha256']={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(H.iterdir()) if p.is_file()}
(H/'manifest.json').write_text(json.dumps(meta,indent=2)+'\n')
