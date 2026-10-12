"""Collect repeatable structural diagnostics, never elapsed-time comparisons."""
import json,hashlib,subprocess,sys
from pathlib import Path
H=Path(__file__).resolve().parent;ROOT=H.parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from run_baseline import hashes
b=json.loads((H/'builds.json').read_text());assert hashes()==b['original_source_sha256'];assert not (H/'manifest.json').exists()
m={'builds':b,'runs':[]}
for workload,n,q in [('dense-bridge-churn-v1',512,90),('redundant-bridge-churn-v1',512,90),('sustained-churn-path-v1',1024,50)]:
 for trial in range(2):
  for variant in ('before','after'):
   v=b['variants'][variant];assert hashlib.sha256(Path(v['binary']).read_bytes()).hexdigest()==v['binary_sha256']
   cmd=[v['binary'],workload,str(n),str(q)];name=f'{workload}-{variant}-{trial}'
   r=subprocess.run(cmd,text=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=120)
   (H/(name+'.json')).write_text(r.stdout);(H/(name+'.stderr.txt')).write_text(r.stderr)
   m['runs'].append({'name':name,'workload':workload,'nodes':n,'query_percent':q,'variant':variant,'trial':trial,'command':cmd,'exit_code':r.returncode});r.check_returncode()
   print(name,flush=True)
assert hashes()==b['original_source_sha256']
m['artifact_sha256']={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in H.iterdir() if p.is_file()}
(H/'manifest.json').write_text(json.dumps(m,indent=2)+'\n')
