"""Reproduce the Cogentco portion of the 2026-10-04 campaign after trace creation.
Usage: python3 THIS_FILE TRACE_PATH NEW_DESTINATION
Run from the benchmark repository root; requires its scripts and release binary.
"""
import hashlib,json,platform,subprocess,sys
from pathlib import Path
sys.path.insert(0,str(Path.cwd()/'scripts'))
from run_baseline import ROOT,CORE,hashes,command,source_patch
from run_scale import peak_rss,run_measurement
trace=Path(sys.argv[1]).resolve();dest=Path(sys.argv[2]).resolve()
data=json.loads(trace.read_text());before=hashes()
binary=ROOT/'target/release/knotrel-benchmarks'
dest.mkdir(parents=True,exist_ok=False)
meta={'purpose':'real-topology-progressive-outages','source_sha256':before,
      'binary_sha256':hashlib.sha256(binary.read_bytes()).hexdigest(),
      'trace_sha256':hashlib.sha256(trace.read_bytes()).hexdigest(),
      'provenance':data['provenance'],'transform':data['transform'],
      'platform':platform.platform(),'compiler':command(['rustc','-vV']),
      'memory_scope':'Peak whole process including importer validation, trace, warmup and sampling; not engine-only.',
      'cases':[]}
for name,root in [('benchmarks',ROOT),('core',CORE)]:
 meta[name]={'revision':command(['git','rev-parse','HEAD'],root),'status':command(['git','status','--porcelain'],root)}
 (dest/(name+'.patch')).write_text(source_patch(root)+'\n')
for name in ['run_scale.py','run_baseline.py','import_topology_zoo.py']:
 (dest/name).write_bytes((ROOT/'scripts'/name).read_bytes())
(dest/'collect.py').write_bytes(Path(__file__).read_bytes())
engines=['compact-bfs','compact-workspace']
for trial in range(4):
 for regime in ['fresh','warmed']:
  offset=trial % len(engines)
  order=engines[offset:]+engines[:offset]
  for engine in order:
   name=f'cogentco-{regime}-p{trial}-{engine}'
   invocation=['/usr/bin/time','-l' if sys.platform=='darwin' else '-v',str(binary),'--trace-in',str(trace),'--engine',engine,'--warmup',str(int(regime=='warmed')),'--repetitions','1']
   result,timeout=run_measurement(invocation,120)
   (dest/(name+'.stderr.txt')).write_text(result.stderr)
   (dest/(name+'.json')).write_text(result.stdout)
   case={'name':name,'trial':trial,'regime':regime,'engine':engine,'command':invocation,'exit_code':result.returncode,'timed_out':timeout,'peak_process_rss_bytes':peak_rss(result.stderr,sys.platform)}
   meta['cases'].append(case)
   (dest/'manifest.partial.json').write_text(json.dumps(meta,indent=2)+'\n')
   result.check_returncode()
   report=json.loads(result.stdout)
   assert report['schema_version']==4 and len(report['repetitions'])==1
   assert report['import']['validated_queries']==sum(op['op']=='connected' for op in data['trace']['operations'])
   assert case['peak_process_rss_bytes'] is not None
   print(name,flush=True)
assert hashes()==before,'sources changed'
(dest/'manifest.partial.json').unlink()
meta['artifact_sha256']={str(p.relative_to(dest)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(dest.rglob('*')) if p.is_file()}
(dest/'manifest.json').write_text(json.dumps(meta,indent=2)+'\n')
