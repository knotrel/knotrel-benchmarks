"""Build two isolated snapshots differing only by an single-pass root/rank lookup."""
import hashlib,json,os,shutil,subprocess,tempfile,sys,difflib
from pathlib import Path
H=Path(__file__).resolve().parent;ROOT=H.parents[1];CORE=ROOT.parent/'knotrel'
sys.path.insert(0,str(ROOT/'scripts'))
from run_baseline import hashes
base=json.loads((ROOT/'results/2026-10-06-engine-ranking-sparse/manifest.json').read_text())
assert hashes()==base['source_sha256']
assert not (H/'builds.json').exists()
work=Path(tempfile.mkdtemp(prefix='knotrel-root-rank-build-'))
for source in (CORE,ROOT):
 dest=work/source.name;dest.mkdir()
 for name in ('Cargo.toml','Cargo.lock','rust-toolchain.toml'):(dest/name).write_bytes((source/name).read_bytes())
 shutil.copytree(source/'crates',dest/'crates')
p=work/'knotrel/crates/knotrel-core/src/hdt_forest.rs';before=p.read_text()
needle="""    fn reroot(&mut self, token: usize) -> Option<usize> {
        let root = self.root(token);
        let rank = self.rank(token);"""
assert before.count(needle)==1
candidate=before.replace(needle,"""    /// Find the tour root and in-order token rank in one parent walk, O(log V).
    /// Moving from a right child adds its parent's left subtree and token.
    fn root_and_rank(&self, mut token: usize) -> (usize, usize) {
        let mut rank = self.size(self.tokens[token].left);
        while let Some(parent) = self.tokens[token].parent {
            if self.tokens[parent].right == Some(token) {
                rank += 1 + self.size(self.tokens[parent].left);
            }
            token = parent;
        }
        (token, rank)
    }
    fn reroot(&mut self, token: usize) -> Option<usize> {
        let (root, rank) = self.root_and_rank(token);""")
(H/'candidate.patch').write_text(''.join(difflib.unified_diff(before.splitlines(True),candidate.splitlines(True),fromfile='a/crates/knotrel-core/src/hdt_forest.rs',tofile='b/crates/knotrel-core/src/hdt_forest.rs')))
meta={'original_source_sha256':base['source_sha256'],'workspace':str(work),'compiler':subprocess.check_output(['rustc','-vV'],text=True),'build_environment':{k:v for k,v in os.environ.items() if k in ('RUSTFLAGS','CARGO_ENCODED_RUSTFLAGS','RUSTC_WRAPPER','CARGO_BUILD_TARGET') or k.startswith('CARGO_PROFILE_RELEASE_')},'variants':{}}
for variant,contents in [('before',before),('after',candidate)]:
 p.write_text(contents)
 cmd=['cargo','build','--release','--locked','--bin','knotrel-benchmarks']
 subprocess.run(cmd,cwd=work/ROOT.name,check=True)
 binary=work/variant;shutil.copy2(work/ROOT.name/'target/release/knotrel-benchmarks',binary)
 meta['variants'][variant]={'binary':str(binary),'binary_sha256':hashlib.sha256(binary.read_bytes()).hexdigest(),'forest_sha256':hashlib.sha256(contents.encode()).hexdigest(),'build_command':cmd}
 (H/(variant+'-forest.rs.txt')).write_text(contents)
assert hashes()==base['source_sha256']
(H/'builds.json').write_text(json.dumps(meta,indent=2)+'\n')
print(work,flush=True)
