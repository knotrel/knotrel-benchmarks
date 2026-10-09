"""Run independent order checks against isolated before/after source copies."""
import json,shutil,subprocess,tempfile
from pathlib import Path
H=Path(__file__).resolve().parent;m=json.loads((H/'builds.json').read_text())
work=Path(tempfile.mkdtemp(prefix='knotrel-join-order-test-'))
test=(H/'candidate-test.rs.txt').read_text();results={}
for v in ('before','after'):
 src=work/v;shutil.copytree(Path(m['workspace'])/'knotrel/crates/knotrel-core/src',src)
 (src/'hdt_forest.rs').write_text((H/(v+'-forest.rs.txt')).read_text()+'\n'+test)
 exe=work/(v+'-test');cmd=['rustc','--edition=2024','--test',str(src/'lib.rs'),'-o',str(exe)]
 build=subprocess.run(cmd,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
 (H/(v+'-test-build.txt')).write_text(build.stdout)
 build.check_returncode();r=subprocess.run([str(exe),'link_preserves_exact_cyclic_order_and_aggregates'],text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
 (H/(v+'-order-test.txt')).write_text(r.stdout);r.check_returncode();results[v]=r.stdout
r=subprocess.run(['cargo','test','--locked','-p','knotrel-core'],cwd=Path(m['workspace'])/'knotrel',text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
(H/'candidate-tests.txt').write_text(r.stdout);r.check_returncode()
(H/'test-results.json').write_text(json.dumps(results,indent=2)+'\n')
print('Both variants preserve explicit cyclic order; candidate complete core tests/doctests passed')
