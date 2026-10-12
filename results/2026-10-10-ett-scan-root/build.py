"""Build frozen current ETT and scan-root reuse candidate in isolated sibling copies."""
import difflib,hashlib,json,shutil,subprocess,tempfile,sys,os
from pathlib import Path
H=Path(__file__).resolve().parent;ROOT=H.parents[1];CORE=ROOT.parent/'knotrel';sys.path.insert(0,str(ROOT/'scripts'))
from run_baseline import hashes
assert not (H/'builds.json').exists()
original=hashes();work=Path(tempfile.mkdtemp(prefix='knotrel-ett-root-',dir='/private/tmp'))
meta={'workspace':str(work),'original_source_sha256':original,'compiler':subprocess.check_output(['rustc','-vV'],text=True),'variants':{},'checkouts':{}}
for source in (ROOT,CORE):
 meta['checkouts'][source.name]={'revision':subprocess.check_output(['git','rev-parse','HEAD'],cwd=source,text=True).strip(),'status':subprocess.check_output(['git','status','--porcelain'],cwd=source,text=True)}
 dest=work/source.name;dest.mkdir()
 for f in ('Cargo.toml','Cargo.lock','rust-toolchain.toml','rustfmt.toml'):
  if (source/f).exists():shutil.copy2(source/f,dest/f)
 shutil.copytree(source/'crates',dest/'crates')
c=work/'knotrel/crates/knotrel-core/src'
before={n:(c/n).read_text() for n in ('forest.rs','dynamic.rs')}
p=c/'forest.rs';p.write_text(before['forest.rs']+'\n'+(H/'scan-test.rs.txt').read_text())
r=subprocess.run(['cargo','test','--locked','-p','knotrel-core','scan_root_tests'],cwd=work/'knotrel',text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT);(H/'red-test.txt').write_text(r.stdout)
assert r.returncode!=0 and 'no method named `contains_vertex`' in r.stdout
s=p.read_text().replace('            forest: self,','            forest: self,\n            root,').replace("    forest: &'a Forest,","    forest: &'a Forest,\n    root: usize,")
s=s.replace("impl Iterator for Candidates<'_> {", """impl Candidates<'_> {
    /// Tests membership in the fixed component selected for this scan.
    /// The immutable forest borrow keeps its root stable, even after iteration
    /// ends. Every yielded source is already in this component, so replacement
    /// search only needs the target's root. O(log V) worst case, O(1) scratch.
    pub(crate) fn contains_vertex(&self, vertex: usize) -> bool {
        self.forest.root(self.forest.vertex_tokens[vertex]) == self.root
    }
}

impl Iterator for Candidates<'_> {""")
p.write_text(s)
s=before['dynamic.rs'].replace("            'search: for v in self.forest.smaller_candidates(a, b) {", "            let mut candidates = self.forest.smaller_candidates(a, b);\n            'search: while let Some(v) = candidates.next() {").replace('if !self.forest.connected(v, w) {','if !candidates.contains_vertex(w) {')
(c/'dynamic.rs').write_text(s)
subprocess.run(['cargo','fmt','--all'],cwd=work/'knotrel',check=True)
after={n:(c/n).read_text() for n in before}
(H/'candidate.patch').write_text(''.join(''.join(difflib.unified_diff(before[n].splitlines(True),after[n].splitlines(True),fromfile='a/crates/knotrel-core/src/'+n,tofile='b/crates/knotrel-core/src/'+n)) for n in before))
for variant,sources in [('before',before),('after',after)]:
 for n,content in sources.items():(c/n).write_text(content);(H/(variant+'-'+n+'.txt')).write_text(content)
 # Compatibility filename for shared verification/audit helpers.
 (H/(variant+'-forest.rs.txt')).write_text(sources['forest.rs'])
 r=subprocess.run(['cargo','test','--locked','-p','knotrel-core'],cwd=work/'knotrel',text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT);(H/(variant+'-tests.txt')).write_text(r.stdout);r.check_returncode()
 r=subprocess.run(['cargo','build','--release','--locked','--bin','knotrel-benchmarks'],cwd=work/ROOT.name,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT);(H/(variant+'-build.txt')).write_text(r.stdout);r.check_returncode()
 binary=work/variant;shutil.copy2(work/ROOT.name/'target/release/knotrel-benchmarks',binary)
 meta['variants'][variant]={'binary':str(binary),'binary_sha256':hashlib.sha256(binary.read_bytes()).hexdigest(),'forest_sha256':hashlib.sha256(sources['forest.rs'].encode()).hexdigest(),'dynamic_sha256':hashlib.sha256(sources['dynamic.rs'].encode()).hexdigest()}
assert hashes()==original
(H/'builds.json').write_text(json.dumps(meta,indent=2)+'\n');print(work)
