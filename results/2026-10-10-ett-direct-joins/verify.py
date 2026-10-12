"""Verify both isolated workspaces using the exact saved candidate."""
import json,os,subprocess
from pathlib import Path
H=Path(__file__).resolve().parent
m=json.loads((H/'builds.json').read_text());work=Path(m['workspace'])
assert (work/'knotrel/crates/knotrel-core/src/forest.rs').read_bytes()==(H/'after-forest.rs.txt').read_bytes()
checks=[['cargo','fmt','--all','--','--check'],['cargo','clippy','--locked','--workspace','--all-targets','--','-D','warnings'],['cargo','test','--locked','--workspace'],['cargo','doc','--locked','--workspace','--no-deps']]
for repo in ('knotrel','knotrel-benchmarks'):
 for i,cmd in enumerate(checks):
  env=os.environ.copy();env['RUSTDOCFLAGS']='-D warnings'
  r=subprocess.run(cmd,cwd=work/repo,env=env,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
  (H/f'{repo}-check-{i}.txt').write_text(r.stdout);r.check_returncode()
(H/'verification.json').write_text(json.dumps({'all_passed':True,'workspaces':['knotrel','knotrel-benchmarks'],'checks':checks},indent=2)+'\n')
print('All integration checks passed')
