"""Isolated counter-only dense replay; normal timed binaries remain frozen."""
import json,shutil,tempfile,subprocess,hashlib
from pathlib import Path
H=Path(__file__).resolve().parent;ROOT=H.parents[1];D=H/'diagnostic';D.mkdir(exist_ok=True);assert not (D/'manifest.json').exists()
b=json.loads((H/'builds.json').read_text());base=Path(b['workspace']);w=Path(tempfile.mkdtemp(prefix='knotrel-root-probe-',dir='/private/tmp'))
for repo in ('knotrel','knotrel-benchmarks'):
 dest=w/repo;dest.mkdir()
 for f in ('Cargo.toml','Cargo.lock','rust-toolchain.toml','rustfmt.toml'):
  if (base/repo/f).exists():shutil.copy2(base/repo/f,dest/f)
 shutil.copytree(base/repo/'crates',dest/'crates')
src=w/'knotrel/crates/knotrel-core/src';original=(src/'index.rs').read_text();s=original
sig='pub(crate) fn root(&self, mut i: usize) -> usize {';assert s.count(sig)==1;s=s.replace(sig,sig+'\n        crate::diagnostics::bump(0);')
pos=s.index(sig);end=s.index('pub(crate) fn rank',pos) if 'pub(crate) fn rank' in s[pos:] else s.index('fn rank',pos)
part=s[pos:end];needle='while let Some(parent) = self.tokens[i].parent.get() {';assert part.count(needle)==1
s=s[:pos]+part.replace(needle,needle+'\n            crate::diagnostics::bump(1);')+s[end:];(src/'index.rs').write_text(s)
(src/'diagnostics.rs').write_bytes((H.parent/'2026-10-10-ett-cut-structure/diagnostics.rs.txt').read_bytes())
p=src/'lib.rs';p.write_text(p.read_text()+'\n/// Counter-only isolated probe.\npub mod diagnostics;\n')
main=w/'knotrel-benchmarks/crates/knotrel-benchmarks/src/bin/ett-structure.rs';main.write_bytes((H.parent/'2026-10-10-ett-cut-structure/main.rs.txt').read_bytes())
m={'workspace':str(w),'runs':[],'scope':'Root calls and parent steps only, phase0=whole operation; no elapsed times'}
for v in ('before','after'):
 for n in ('forest.rs','dynamic.rs'):(src/n).write_bytes((H/(v+'-'+n+'.txt')).read_bytes())
 subprocess.run(['cargo','fmt','--all'],cwd=w/'knotrel',check=True);subprocess.run(['cargo','fmt','--all'],cwd=w/'knotrel-benchmarks',check=True)
 r=subprocess.run(['cargo','build','--locked','--release','--bin','ett-structure'],cwd=w/'knotrel-benchmarks',text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT);(D/(v+'-build.txt')).write_text(r.stdout);r.check_returncode()
 binary=w/v;shutil.copy2(w/'knotrel-benchmarks/target/release/ett-structure',binary)
 for t in range(2):
  cmd=[str(binary),'dense-bridge-churn-v1','512','90'];r=subprocess.run(cmd,text=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=120);r.check_returncode()
  name=f'{v}-{t}';(D/(name+'.json')).write_text(r.stdout);(D/(name+'.stderr.txt')).write_text(r.stderr);m['runs'].append({'name':name,'variant':v,'command':cmd,'binary_sha256':hashlib.sha256(binary.read_bytes()).hexdigest(),'exit_code':r.returncode})
(D/'instrumented-index.rs.txt').write_bytes((src/'index.rs').read_bytes());(D/'main.rs.txt').write_bytes(main.read_bytes());(D/'diagnostics.rs.txt').write_bytes((src/'diagnostics.rs').read_bytes())
m['artifact_sha256']={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in D.iterdir() if p.is_file()}
(D/'manifest.json').write_text(json.dumps(m,indent=2)+'\n')
print('Counter-only probe completed')
