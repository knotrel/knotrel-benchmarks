"""Build identical diagnostic hooks over the two frozen ETT variants."""
import json,hashlib,shutil,subprocess,tempfile,sys,difflib
from pathlib import Path
H=Path(__file__).resolve().parent;ROOT=H.parents[1];CORE=ROOT.parent/'knotrel';P=H.parent/'2026-10-10-ett-direct-joins'
sys.path.insert(0,str(ROOT/'scripts'));from run_baseline import hashes
base=json.loads((P/'builds.json').read_text());assert hashes()==base['original_source_sha256']
assert not (H/'builds.json').exists();work=Path(tempfile.mkdtemp(prefix='knotrel-ett-cut-',dir='/private/tmp'))
for source in (ROOT,CORE):
 dest=work/source.name;dest.mkdir()
 for f in ('Cargo.toml','Cargo.lock','rust-toolchain.toml','rustfmt.toml'):
  if (source/f).exists():shutil.copy2(source/f,dest/f)
 shutil.copytree(source/'crates',dest/'crates')
c=work/'knotrel/crates/knotrel-core/src'
(c/'diagnostics.rs').write_bytes((H/'diagnostics.rs.txt').read_bytes())
p=c/'lib.rs';p.write_text(p.read_text()+'\n/// Isolated diagnostic counters, not a production interface.\npub mod diagnostics;\n')
p=c/'dynamic.rs';s=p.read_text();s=s.replace('            self.forest.cut(arcs);','            { let _phase = crate::diagnostics::enter(1); self.forest.cut(arcs); }')
s=s.replace("            'search: for v", "            let search_phase = crate::diagnostics::enter(2);\n            'search: for v")
s=s.replace('            if let Some((v, w)) = replacement {','            drop(search_phase);\n            if let Some((v, w)) = replacement {\n                let _phase = crate::diagnostics::enter(3);');p.write_text(s)
(work/'knotrel-benchmarks/crates/knotrel-benchmarks/src/bin/ett-structure.rs').write_bytes((H/'main.rs.txt').read_bytes())
meta={'workspace':str(work),'original_source_sha256':base['original_source_sha256'],'variants':{},'compiler':subprocess.check_output(['rustc','-vV'],text=True)}
for variant in ('before','after'):
 s=(P/(variant+'-forest.rs.txt')).read_text();assert hashlib.sha256(s.encode()).hexdigest()==base['variants'][variant]['forest_sha256']
 for signature,counter in [('fn root(&self, mut i: usize) -> usize {',0),('fn rank(&self, mut i: usize) -> usize {',2),('fn split(&mut self, root: Option<usize>, k: usize) -> (Option<usize>, Option<usize>) {',4),('fn join(&mut self, left: Option<usize>, pivot: usize, right: Option<usize>) -> usize {',5),('fn pull(&mut self, i: usize) {',6),('fn rotate_left(&mut self, i: usize) -> usize {',7),('fn rotate_right(&mut self, i: usize) -> usize {',7)]:
  assert s.count(signature)==1;s=s.replace(signature,signature+f'\n        crate::diagnostics::bump({counter});')
 needle='while let Some(parent) = self.tokens[i].parent.get() {'
 assert s.count(needle)==2;s=s.replace(needle,needle+'\n            crate::diagnostics::bump(1);',1)
 pos=s.index('fn rank(');s=s[:pos]+s[pos:].replace(needle,needle+'\n            crate::diagnostics::bump(3);',1)
 s=s.replace('while let Some(i) = self.stack.pop() {','while let Some(i) = self.stack.pop() {\n            crate::diagnostics::bump(8);')
 s=s.replace('while let Some(i) = current {','while let Some(i) = current {\n            crate::diagnostics::bump(9);')
 (c/'forest.rs').write_text(s)
 subprocess.run(['cargo','fmt','--all'],cwd=work/'knotrel',check=True)
 subprocess.run(['cargo','fmt','--all'],cwd=work/'knotrel-benchmarks',check=True)
 (H/(variant+'-forest.rs.txt')).write_bytes((c/'forest.rs').read_bytes())
 r=subprocess.run(['cargo','test','--locked','-p','knotrel-core'],cwd=work/'knotrel',text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT);(H/(variant+'-tests.txt')).write_text(r.stdout);r.check_returncode()
 r=subprocess.run(['cargo','build','--release','--locked','--bin','ett-structure'],cwd=work/'knotrel-benchmarks',text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT);(H/(variant+'-build.txt')).write_text(r.stdout);r.check_returncode()
 binary=work/variant;shutil.copy2(work/'knotrel-benchmarks/target/release/ett-structure',binary)
 meta['variants'][variant]={'binary':str(binary),'binary_sha256':hashlib.sha256(binary.read_bytes()).hexdigest(),'original_forest_sha256':base['variants'][variant]['forest_sha256']}
for name in ('dynamic.rs','diagnostics.rs'):(H/(name+'.txt')).write_bytes((c/name).read_bytes())
meta['instrumented_source_sha256']={str(p.relative_to(work)):hashlib.sha256(p.read_bytes()).hexdigest() for p in work.rglob('*.rs') if 'target' not in p.parts}
assert hashes()==base['original_source_sha256'];(H/'builds.json').write_text(json.dumps(meta,indent=2)+'\n');print(work)
