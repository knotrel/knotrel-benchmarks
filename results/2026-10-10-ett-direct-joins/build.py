"""Build frozen current ETT and direct-join candidate in isolated sibling copies."""
import difflib,hashlib,json,shutil,subprocess,tempfile,sys,os
from pathlib import Path
H=Path(__file__).resolve().parent;ROOT=H.parents[1];CORE=ROOT.parent/'knotrel';sys.path.insert(0,str(ROOT/'scripts'))
from run_baseline import hashes
assert not (H/'builds.json').exists()
original=hashes();work=Path(tempfile.mkdtemp(prefix='knotrel-ett-direct-',dir='/private/tmp'))
meta={'workspace':str(work),'original_source_sha256':original,'compiler':subprocess.check_output(['rustc','-vV'],text=True),'variants':{},'checkouts':{}}
for source in (ROOT,CORE):
 meta['checkouts'][source.name]={'revision':subprocess.check_output(['git','rev-parse','HEAD'],cwd=source,text=True).strip(),'status':subprocess.check_output(['git','status','--porcelain'],cwd=source,text=True)}
 dest=work/source.name;dest.mkdir()
 for f in ('Cargo.toml','Cargo.lock','rust-toolchain.toml','rustfmt.toml'):
  if (source/f).exists():shutil.copy2(source/f,dest/f)
 shutil.copytree(source/'crates',dest/'crates')
p=work/'knotrel/crates/knotrel-core/src/forest.rs';before=p.read_text()
old='''        let left = self.concat(left, Some(ab));
        let left = self.concat(left, right);
        self.concat(left, Some(ba));'''
new='''        // New edge tokens are already available as AVL join pivots. Preserve
        // the tour order left, ab, right, ba without extracting more pivots.
        // The two joins preserve balance and O(log V) worst-case link cost.
        let tour = self.join(left, ab, right);
        self.join(Some(tour), ba, None);'''
assert before.count(old)==1
after=before.replace(old,new)
(H/'candidate.patch').write_text(''.join(difflib.unified_diff(before.splitlines(True),after.splitlines(True),fromfile='a/crates/knotrel-core/src/forest.rs',tofile='b/crates/knotrel-core/src/forest.rs')))
for variant,source in [('before',before),('after',after)]:
 p.write_text(source);(H/(variant+'-forest.rs.txt')).write_text(source)
 r=subprocess.run(['cargo','test','--locked','-p','knotrel-core'],cwd=work/'knotrel',text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT);(H/(variant+'-tests.txt')).write_text(r.stdout);r.check_returncode()
 r=subprocess.run(['cargo','build','--release','--locked','--bin','knotrel-benchmarks'],cwd=work/ROOT.name,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT);(H/(variant+'-build.txt')).write_text(r.stdout);r.check_returncode()
 binary=work/variant;shutil.copy2(work/ROOT.name/'target/release/knotrel-benchmarks',binary)
 meta['variants'][variant]={'binary':str(binary),'binary_sha256':hashlib.sha256(binary.read_bytes()).hexdigest(),'forest_sha256':hashlib.sha256(source.encode()).hexdigest()}
assert hashes()==original
(H/'builds.json').write_text(json.dumps(meta,indent=2)+'\n');print(work)
