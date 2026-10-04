"""macOS diagnostic sampling of a longer HDT cyclic-block run, not timing evidence."""
import hashlib,json,subprocess,sys
from pathlib import Path
ROOT=Path.cwd();OUT=ROOT/'results/2026-10-04-hdt-cpu-profile'
sys.path.insert(0,str(ROOT/'scripts'))
from run_baseline import hashes
binary=ROOT/'target/release/knotrel-benchmarks'
args=[str(binary),'--engine','hdt','--nodes','100000','--rounds','1000','--query-percent','90','--workload','sustained-churn-blocks-v1','--warmup','0','--repetitions','10','--seed','42']
meta={'scope':'Diagnostic CPU stack sampling; includes setup, replay and teardown; longer trace than reference; do not compare these timings with normal benchmark results.','command':args,'source_sha256':hashes(),'binary_sha256':hashlib.sha256(binary.read_bytes()).hexdigest()}
with (OUT/'diagnostic-run.json').open('x') as stdout,(OUT/'diagnostic-run.stderr.txt').open('x') as stderr:
 process=subprocess.Popen(args,stdout=stdout,stderr=stderr)
 sample=['/usr/bin/sample',str(process.pid),'5','1','-mayDie','-file',str(OUT/'sample.txt')]
 sampled=subprocess.run(sample,text=True,capture_output=True,timeout=30)
 (OUT/'sampler.stderr.txt').write_text(sampled.stderr+sampled.stdout)
 try: code=process.wait(timeout=180)
 except subprocess.TimeoutExpired:
  process.kill();process.wait();raise
meta.update({'sampler_command':sample,'sampler_exit_code':sampled.returncode,'benchmark_exit_code':code})
(OUT/'manifest.json').write_text(json.dumps(meta,indent=2)+'\n')
assert code==0 and sampled.returncode==0
