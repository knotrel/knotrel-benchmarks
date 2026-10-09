"""Run deterministic structural counts outside all timed matrix processes."""
import hashlib,json,subprocess,sys,os
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from run_baseline import hashes,source_patch,command
out=HERE/'diagnostics';out.mkdir(exist_ok=False)
comparison=json.loads((HERE/'comparison.json').read_text())['rows']
rows=[r for r in comparison if r['family']!='cogentco' and r['regime']=='fresh']
binary=ROOT/'target/release/traversal-profile'
meta={'scope':'Structural counts only; no diagnostic timing is a benchmark','source_sha256':hashes(),'binary_sha256':hashlib.sha256(binary.read_bytes()).hexdigest(),'compiler':command(['rustc','-vV']),'cases':[]}
(out/'benchmarks.patch').write_text(source_patch(ROOT)+'\n')
for name in ['traversal.rs','bin/traversal-profile.rs']:
 (out/(Path(name).name+'.txt')).write_bytes((ROOT/'crates/knotrel-benchmarks/src'/name).read_bytes())
meta['build_command']=['cargo','build','--release','--locked','--bin','traversal-profile']
meta['environment']={k:os.environ.get(k) for k in ['RUSTFLAGS','CARGO_ENCODED_RUSTFLAGS','CARGO_BUILD_TARGET','CARGO_TARGET_DIR','CARGO_PROFILE_RELEASE_OPT_LEVEL','CARGO_PROFILE_RELEASE_LTO','CARGO_PROFILE_RELEASE_CODEGEN_UNITS']}
for r in rows:
 name=f"{r['workload']}-n{r['nodes']}-q{r['query_percent']}"
 cmd=[str(binary),str(r['nodes']),r['workload'],str(r['query_percent'])]
 a=subprocess.check_output(cmd,text=True,timeout=120);b=subprocess.check_output(cmd,text=True,timeout=120)
 assert a==b,'instrumented repeats must be identical'
 report=json.loads(a);assert report['trace_fingerprint_fnv1a64']==r['fingerprint']
 (out/(name+'.json')).write_text(a)
 meta['cases'].append({'name':name,'command':cmd,'equal_runs':2})
 print(name,flush=True)
assert hashes()==meta['source_sha256']
meta['artifact_sha256']={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(out.iterdir()) if p.is_file()}
(out/'manifest.json').write_text(json.dumps(meta,indent=2)+'\n')
