"""Build two isolated snapshots differing only by promotion-only right-associated tour joins."""
import hashlib,json,os,shutil,subprocess,tempfile,sys,difflib
from pathlib import Path
H=Path(__file__).resolve().parent;ROOT=H.parents[1];CORE=ROOT.parent/'knotrel'
sys.path.insert(0,str(ROOT/'scripts'))
from run_baseline import hashes
base=json.loads((ROOT/'results/2026-10-06-engine-ranking-sparse/manifest.json').read_text())
assert hashes()==base['source_sha256']
assert not (H/'builds.json').exists()
work=Path(tempfile.mkdtemp(prefix='knotrel-promotion-joins-build-',dir='/private/tmp'))
for source in (CORE,ROOT):
 dest=work/source.name;dest.mkdir()
 for name in ('Cargo.toml','Cargo.lock','rust-toolchain.toml'):(dest/name).write_bytes((source/name).read_bytes())
 shutil.copytree(source/'crates',dest/'crates')
p=work/'knotrel/crates/knotrel-core/src/hdt_forest.rs';before=p.read_text()
hd=work/'knotrel/crates/knotrel-core/src/hdt.rs';before_hdt=hd.read_text()
signature='    pub(crate) fn link(&mut self, a: usize, b: usize) -> (usize, usize) {'
assert before.count(signature)==1
candidate=before.replace(signature,"""    pub(crate) fn link(&mut self, a: usize, b: usize) -> (usize, usize) {
        self.link_ordered::<false>(a, b)
    }
    /// Join a promoted tree edge, preserving the exact cyclic tour sequence.
    /// Promotions usually attach a small right tour, so join that side first.
    /// Both associations preserve AVL invariants and O(log V) worst-case cost.
    pub(crate) fn link_promoted(&mut self, a: usize, b: usize) -> (usize, usize) {
        self.link_ordered::<true>(a, b)
    }
    fn link_ordered<const RIGHT_FIRST: bool>(&mut self, a: usize, b: usize) -> (usize, usize) {""")
needle="""        let tour = self.join(left, ab, right);
        self.join(Some(tour), ba, None);"""
assert candidate.count(needle)==1
candidate=candidate.replace(needle,"""        if RIGHT_FIRST {
            let right = self.join(right, ba, None);
            self.join(left, ab, Some(right));
        } else {
            let tour = self.join(left, ab, right);
            self.join(Some(tour), ba, None);
        }""")
needle='Some(self.levels[i + 1].forest.link(local_a, local_b))'
assert before_hdt.count(needle)==1
candidate_hdt=before_hdt.replace(needle,'Some(self.levels[i + 1].forest.link_promoted(local_a, local_b))')
patch=''
for name,b,a in [('hdt_forest.rs',before,candidate),('hdt.rs',before_hdt,candidate_hdt)]:
 patch+=''.join(difflib.unified_diff(b.splitlines(True),a.splitlines(True),fromfile='a/crates/knotrel-core/src/'+name,tofile='b/crates/knotrel-core/src/'+name))
(H/'candidate.patch').write_text(patch)
meta={'original_source_sha256':base['source_sha256'],'workspace':str(work),'compiler':subprocess.check_output(['rustc','-vV'],text=True),'build_environment':{k:v for k,v in os.environ.items() if k in ('RUSTFLAGS','CARGO_ENCODED_RUSTFLAGS','RUSTC_WRAPPER','CARGO_BUILD_TARGET') or k.startswith('CARGO_PROFILE_RELEASE_')},'variants':{}}
for variant,contents in [('before',before),('after',candidate)]:
 p.write_text(contents)
 hdcontents=before_hdt if variant=='before' else candidate_hdt
 hd.write_text(hdcontents)
 (H/(variant+'-hdt.rs.txt')).write_text(hdcontents)
 cmd=['cargo','build','--release','--locked','--bin','knotrel-benchmarks']
 subprocess.run(cmd,cwd=work/ROOT.name,check=True)
 binary=work/variant;shutil.copy2(work/ROOT.name/'target/release/knotrel-benchmarks',binary)
 meta['variants'][variant]={'binary':str(binary),'binary_sha256':hashlib.sha256(binary.read_bytes()).hexdigest(),'forest_sha256':hashlib.sha256(contents.encode()).hexdigest(),'hdt_sha256':hashlib.sha256(hdcontents.encode()).hexdigest(),'build_command':cmd}
 (H/(variant+'-forest.rs.txt')).write_text(contents)
assert hashes()==base['source_sha256']
(H/'builds.json').write_text(json.dumps(meta,indent=2)+'\n')
print(work,flush=True)
