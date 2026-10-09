"""Replay the preserved real topology on the same binary as the scale matrix."""
import hashlib,json,random,sys,platform,itertools
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'scripts'))
from run_baseline import ROOT,hashes
from run_scale import run_measurement,peak_rss
OUT=ROOT/'results/2026-10-05-traversal-order-cogentco'
OUT.mkdir(exist_ok=False)
base=json.loads((ROOT/'results/2026-10-05-traversal-order-sparse/manifest.json').read_text())
binary=ROOT/'target/release/knotrel-benchmarks'
assert hashlib.sha256(binary.read_bytes()).hexdigest()==base['binary_sha256']
assert hashes()==base['source_sha256']
reference=json.loads((ROOT/'results/2026-10-04-cogentco-campaign/manifest.json').read_text())
source=next(c for c in reference['cases'] if c['engine']=='compact-bfs')
args=source['command'][3:]
# Preserve import semantics and discard reference output path only.
if '--trace-out' in args:
 i=args.index('--trace-out');del args[i:i+2]
trace=Path(args[args.index('--trace-in')+1])
meta={'source_sha256':base['source_sha256'],'binary_sha256':base['binary_sha256'],'environment':base['environment'],'core':base['core'],'benchmarks':base['benchmarks'],'trace_sha256':hashlib.sha256(trace.read_bytes()).hexdigest(),'cases':[]}
cases=list(itertools.product(range(3),['fresh','warmed'],['traversal-bfs','traversal-dfs','compact-workspace','petgraph-dfs']))
random.Random(42).shuffle(cases)
for trial,regime,engine in cases:
 a=list(args);a[a.index('--engine')+1]=engine;a[a.index('--warmup')+1]=str(int(regime=='warmed'));a[a.index('--repetitions')+1]='1'
 name=f'cogentco-{regime}-p{trial}-{engine}';cmd=['/usr/bin/time','-l',str(binary),*a]
 result,timeout=run_measurement(cmd,120)
 (OUT/(name+'.stderr.txt')).write_text(result.stderr)
 case=dict(name=name,trial=trial,regime=regime,engine=engine,command=cmd,timed_out=timeout,exit_code=result.returncode,peak_process_rss_bytes=peak_rss(result.stderr,sys.platform))
 meta['cases'].append(case)
 (OUT/(name+('.json' if result.returncode==0 else '.partial-stdout.txt'))).write_text(result.stdout)
 if result.returncode==0:json.loads(result.stdout)
assert hashes()==base['source_sha256']
meta['artifact_sha256']={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(OUT.iterdir()) if p.is_file()}
(OUT/'manifest.json').write_text(json.dumps(meta,indent=2)+'\n')
