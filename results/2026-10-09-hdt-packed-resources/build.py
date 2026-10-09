"""Apply identical diagnostic markers to the saved packed-token binary pair."""
import hashlib,json,shutil,subprocess,tempfile,sys
from pathlib import Path
H=Path(__file__).resolve().parent;ROOT=H.parents[1];CORE=ROOT.parent/'knotrel';sys.path.insert(0,str(ROOT/'scripts'))
from run_baseline import hashes
P=H.parent/'2026-10-08-hdt-packed-tokens';D=H.parent/'2026-10-08-hdt-phase-resources';base=json.loads((P/'builds.json').read_text());diag=json.loads((D/'builds.json').read_text());assert hashes()==base['original_source_sha256']
work=Path(tempfile.mkdtemp(prefix='knotrel-packed-resources-',dir='/private/tmp'))
for source in (CORE,ROOT):
 dest=work/source.name;dest.mkdir()
 for f in ('Cargo.toml','Cargo.lock','rust-toolchain.toml'):(dest/f).write_bytes((source/f).read_bytes())
 shutil.copytree(source/'crates',dest/'crates')
main=(D/'after-main.rs.txt').read_bytes();assert hashlib.sha256(main).hexdigest()==diag['diagnostic_source_sha256'];(work/ROOT.name/'crates/knotrel-benchmarks/src/main.rs').write_bytes(main);(H/'diagnostic-main.rs.txt').write_bytes(main);(H/'diagnostic.patch').write_bytes((D/'diagnostic.patch').read_bytes())
meta={'workspace':str(work),'original_source_sha256':base['original_source_sha256'],'main_sha256':hashlib.sha256(main).hexdigest(),'compiler':subprocess.check_output(['rustc','-vV'],text=True),'variants':{}}
for v,b in base['variants'].items():
 content=(P/(v+'-forest.rs.txt')).read_bytes();assert hashlib.sha256(content).hexdigest()==b['forest_sha256'];(work/'knotrel/crates/knotrel-core/src/hdt_forest.rs').write_bytes(content);(H/(v+'-forest.rs.txt')).write_bytes(content)
 r=subprocess.run(['cargo','build','--release','--locked','--bin','knotrel-benchmarks'],cwd=work/ROOT.name,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT);(H/(v+'-build.txt')).write_text(r.stdout);r.check_returncode()
 binary=work/v;shutil.copy2(work/ROOT.name/'target/release/knotrel-benchmarks',binary);meta['variants'][v]={'binary':str(binary),'binary_sha256':hashlib.sha256(binary.read_bytes()).hexdigest(),'forest_sha256':b['forest_sha256']}
assert hashes()==base['original_source_sha256'];(H/'builds.json').write_text(json.dumps(meta,indent=2)+'\n');print(work)
