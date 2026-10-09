"""Reconstruct the saved candidate for final checks, independently of old temp builds."""
import hashlib,json,os,shutil,subprocess,sys,tempfile
from pathlib import Path
H=Path(__file__).resolve().parent;ROOT=H.parents[1];CORE=ROOT.parent/'knotrel'
sys.path.insert(0,str(ROOT/'scripts'))
from run_baseline import hashes
m=json.loads((H/'builds.json').read_text());assert hashes()==m['original_source_sha256']
work=Path(tempfile.mkdtemp(prefix='knotrel-promotion-joins-verification-',dir='/private/tmp'));cwd=work/'knotrel';cwd.mkdir()
for name in ('Cargo.toml','Cargo.lock','rust-toolchain.toml'):(cwd/name).write_bytes((CORE/name).read_bytes())
shutil.copytree(CORE/'crates',cwd/'crates')
p=cwd/'crates/knotrel-core/src/hdt_forest.rs';p.write_bytes((H/'after-forest.rs.txt').read_bytes());assert hashlib.sha256(p.read_bytes()).hexdigest()==m['variants']['after']['forest_sha256']
p=cwd/'crates/knotrel-core/src/hdt.rs';p.write_bytes((H/'after-hdt.rs.txt').read_bytes());assert hashlib.sha256(p.read_bytes()).hexdigest()==m['variants']['after']['hdt_sha256']
checks=[['cargo','fmt','--all','--','--check'],['cargo','clippy','--locked','--workspace','--all-targets','--','-D','warnings'],['cargo','test','--locked','--workspace'],['cargo','doc','--locked','--workspace','--no-deps']]
for i,cmd in enumerate(checks):
 env=os.environ.copy()
 if i==3:env['RUSTDOCFLAGS']='-D warnings'
 r=subprocess.run(cmd,cwd=cwd,env=env,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT);(H/f'reconstructed-candidate-check-{i}.txt').write_text(r.stdout);r.check_returncode()
(H/'reconstruction-verification.json').write_text(json.dumps({'directory':str(work),'forest_sha256':m['variants']['after']['forest_sha256'],'checks':checks,'all_passed':True,'note':'Fresh reconstruction verifies the saved candidate independently of temporary measurement binaries; original test and measurement logs remain unchanged.'},indent=2)+'\n')
print('Saved candidate reconstructed with exact source hash; format, Clippy, core tests/doctests and Rustdoc passed')
