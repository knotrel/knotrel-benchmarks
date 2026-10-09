"""Build isolated baseline versus packed optional token indices, no algorithm change."""
import difflib,hashlib,json,shutil,subprocess,tempfile,sys,re
from pathlib import Path
H=Path(__file__).resolve().parent;ROOT=H.parents[1];CORE=ROOT.parent/'knotrel';sys.path.insert(0,str(ROOT/'scripts'))
from run_baseline import hashes
base={'original_source_sha256':hashes()}
assert not (H/'builds.json').exists();work=Path(tempfile.mkdtemp(prefix='knotrel-ett-packed-',dir='/private/tmp'))
for source in (ROOT,CORE):
 dest=work/source.name;dest.mkdir()
 for f in ('Cargo.toml','Cargo.lock','rust-toolchain.toml'):(dest/f).write_bytes((source/f).read_bytes())
 shutil.copytree(source/'crates',dest/'crates')
p=work/'knotrel/crates/knotrel-core/src/forest.rs';before=p.read_text()
p.write_text(before+'\n'+(H/'layout-test.rs.txt').read_text())
r=subprocess.run(['cargo','test','--locked','-p','knotrel-core','forest::compact_layout_tests'],cwd=work/'knotrel',text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
(H/'red-test.txt').write_text(r.stdout)
assert r.returncode!=0 and 'left: 96' in r.stdout and 'right: 64' in r.stdout, r.stdout
p.write_text(before)
helper='''
/// Optional arena index encoded as index + 1, leaving zero for absence.
/// Every stored index names a Vec element, hence cannot be usize::MAX.
/// Checked encoding rejects invalid sentinel overflow; decoding is O(1).
#[derive(Clone, Copy, Debug, Default)]
struct Index(Option<std::num::NonZeroUsize>);
impl Index {
    const NONE: Self = Self(None);
    fn from(value: Option<usize>) -> Self {
        Self(value.map(|i| std::num::NonZeroUsize::new(i.checked_add(1).expect("arena index overflow")).expect("encoded index is nonzero")))
    }
    fn get(self) -> Option<usize> { self.0.map(|i| i.get() - 1) }
    fn take(&mut self) -> Option<usize> { let old = self.get(); *self = Self::NONE; old }
}
'''
s=before
for field in ('left','right','parent','vertex'):
 s=s.replace(field+': Option<usize>,',field+': Index,',1)
 s=re.sub(r'\.'+field+r'\b', '.'+field+'.get()',s)
s=s.replace('.get().take()', '.take()')
s=re.sub(r'(self\.tokens\[[^\n]+?\]\.(?:left|right|parent|vertex))\.get\(\) = ([^\n]+);',r'\1 = Index::from(\2);',s)
for field in ('left','right','parent'):s=s.replace(field+': None,',field+': Index::NONE,',1)
s=s.replace('            vertex,','            vertex: Index::from(vertex),',1)
s=s.replace('#[derive(Debug)]\nstruct Token',helper+'\n#[derive(Debug)]\nstruct Token',1)
s+='\n'+(H/'layout-test.rs.txt').read_text()+'''
#[cfg(test)]
mod index_tests {
    use super::Index;
    #[test]
    fn optional_indices_round_trip_and_clear() {
        assert_eq!(size_of::<Index>(), size_of::<usize>());
        for value in [None, Some(0), Some(1), Some(usize::MAX - 1)] {
            let mut index = Index::from(value);
            assert_eq!(index.get(), value);
            assert_eq!(index.take(), value);
            assert_eq!(index.get(), None);
        }
    }
    #[test]
    #[should_panic(expected = "arena index overflow")]
    fn rejects_unrepresentable_index_without_wrapping() { Index::from(Some(usize::MAX)); }
}
'''
p.write_text(s);subprocess.run(['cargo','fmt','--all'],cwd=work/'knotrel',check=True);after=p.read_text()
(H/'candidate.patch').write_text(''.join(difflib.unified_diff(before.splitlines(True),after.splitlines(True),fromfile='a/crates/knotrel-core/src/forest.rs',tofile='b/crates/knotrel-core/src/forest.rs')))
meta={'workspace':str(work),'original_source_sha256':base['original_source_sha256'],'compiler':subprocess.check_output(['rustc','-vV'],text=True),'variants':{}}
for variant,content in [('before',before),('after',after)]:
 p.write_text(content);(H/(variant+'-forest.rs.txt')).write_text(content)
 if variant=='after':
  r=subprocess.run(['cargo','test','--locked','-p','knotrel-core'],cwd=work/'knotrel',text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT);(H/'candidate-tests.txt').write_text(r.stdout);r.check_returncode()
 cmd=['cargo','build','--release','--locked','--bin','knotrel-benchmarks'];r=subprocess.run(cmd,cwd=work/ROOT.name,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT);(H/(variant+'-build.txt')).write_text(r.stdout);r.check_returncode()
 binary=work/variant;shutil.copy2(work/ROOT.name/'target/release/knotrel-benchmarks',binary);meta['variants'][variant]={'binary':str(binary),'binary_sha256':hashlib.sha256(binary.read_bytes()).hexdigest(),'forest_sha256':hashlib.sha256(content.encode()).hexdigest()}
assert hashes()==base['original_source_sha256'];(H/'builds.json').write_text(json.dumps(meta,indent=2)+'\n');print(work)
