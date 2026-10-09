"""Run independent order checks against isolated before/after source copies."""
import json,shutil,subprocess,tempfile
from pathlib import Path
H=Path(__file__).resolve().parent;m=json.loads((H/'builds.json').read_text())
work=Path(tempfile.mkdtemp(prefix='knotrel-root-rank-test-'))
test=(H/'candidate-test.rs.txt').read_text();results={}
for v in ('before','after'):
 src=work/v;shutil.copytree(Path(m['workspace'])/'knotrel/crates/knotrel-core/src',src)
 (src/'hdt_forest.rs').write_text((H/(v+'-forest.rs.txt')).read_text()+'\n'+test)
 exe=work/(v+'-test');cmd=['rustc','--edition=2024','--test',str(src/'lib.rs'),'-o',str(exe)]
 build=subprocess.run(cmd,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
 (H/(v+'-test-build.txt')).write_text(build.stdout)
 if v=='before':
  assert build.returncode!=0 and 'no method named `root_and_rank`' in build.stdout
  results[v]='expected missing-method failure';continue
 build.check_returncode();r=subprocess.run([str(exe),'root_and_rank_matches_explicit_order_after_updates'],text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
 (H/'candidate-order-test.txt').write_text(r.stdout);r.check_returncode();results[v]=r.stdout
r=subprocess.run(['cargo','test','--locked','-p','knotrel-core'],cwd=Path(m['workspace'])/'knotrel',text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
(H/'candidate-tests.txt').write_text(r.stdout);r.check_returncode()
(H/'test-results.json').write_text(json.dumps(results,indent=2)+'\n')
print('Baseline missing-method failure verified; candidate explicit-order test and complete core tests/doctests passed')
