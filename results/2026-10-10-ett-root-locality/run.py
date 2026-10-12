"""Root-parent locality probe; no elapsed-time conclusions."""
import hashlib,json,shutil,subprocess,tempfile,os
from pathlib import Path
H=Path(__file__).resolve().parent;P=H.parent/'2026-10-10-ett-scan-root'
assert not (H/'manifest.json').exists()
b=json.loads((P/'builds.json').read_text());base=Path(b['workspace']);w=Path(tempfile.mkdtemp(prefix='knotrel-root-locality-'))
for repo in ('knotrel','knotrel-benchmarks'):shutil.copytree(base/repo,w/repo,ignore=shutil.ignore_patterns('target','.git','results','__pycache__'))
core=w/'knotrel';bench=w/'knotrel-benchmarks';src=core/'crates/knotrel-core/src'
(src/'diagnostics.rs').write_bytes((H/'diagnostics.rs.txt').read_bytes())
p=src/'lib.rs';p.write_text(p.read_text()+'\n/// Isolated replay locality diagnostics.\npub mod diagnostics;\n')
p=src/'index.rs';s=p.read_text();old='''        while let Some(parent) = self.tokens[i].parent.get() {
            i = parent;
        }
        i
''';new='''        loop {
            crate::diagnostics::record(i, &self.tokens[i].parent as *const _ as usize, self.tokens.as_ptr() as usize);
            match self.tokens[i].parent.get() {
                Some(parent) => i = parent,
                None => break,
            }
        }
        i
''';assert s.count(old)==1;p.write_text(s.replace(old,new))
p=bench/'crates/knotrel-benchmarks/src/main.rs';s=p.read_text().replace('    workload_wall_ns: u128,','    workload_wall_ns: u128,\n    root_accesses: Vec<[usize; 2]>,').replace('    let wall_start = Instant::now();','    knotrel_core::diagnostics::begin();\n    let wall_start = Instant::now();').replace('    let workload_wall_ns = wall_start.elapsed().as_nanos();','    let workload_wall_ns = wall_start.elapsed().as_nanos();\n    let root_accesses = knotrel_core::diagnostics::finish();').replace('        workload_wall_ns,','        workload_wall_ns,\n        root_accesses,');p.write_text(s)
for repo in (core,bench):subprocess.run(['cargo','fmt','--all'],cwd=repo,check=True)
m={'workspace':str(w),'page_bytes':16384,'line_bytes':128,'scope':'Parent field reads in GenericForest::root only; no cache misses or timing claims','runs':[]}
for v in ('before','after'):
 for name in ('forest','dynamic'):(src/f'{name}.rs').write_bytes((P/f'{v}-{name}.rs.txt').read_bytes())
 with (H/f'{v}-build.txt').open('w') as log:subprocess.run(['cargo','build','--offline','--locked','--release','--bin','knotrel-benchmarks'],cwd=bench,stdout=log,stderr=log,check=True)
 binary=w/v;shutil.copy2(bench/'target/release/knotrel-benchmarks',binary)
 for warmup in (0,1):
  for trial in range(2):
   cmd=[str(binary),'--nodes','1000000','--rounds','10','--workload','sustained-churn-path-v1','--query-percent','50','--engine','ett-scan','--warmup',str(warmup),'--repetitions','1','--seed','42','--query-repeats','0']
   r=subprocess.run(cmd,capture_output=True,text=True,timeout=120);name=f'{v}-w{warmup}-t{trial}'
   (H/(name+'.json')).write_text(r.stdout);(H/(name+'.stderr.txt')).write_text(r.stderr)
   m['runs'].append({'name':name,'variant':v,'warmup':warmup,'trial':trial,'command':cmd,'exit_code':r.returncode,'binary_sha256':hashlib.sha256(binary.read_bytes()).hexdigest()});r.check_returncode()
for label,p in [('main.rs.txt',bench/'crates/knotrel-benchmarks/src/main.rs'),('index.rs.txt',src/'index.rs'),('diagnostics.rs.txt',src/'diagnostics.rs')]: (H/label).write_bytes(p.read_bytes())
checks=[]
for repo in (core,bench):
 for i,cmd in enumerate([['cargo','fmt','--all','--','--check'],['cargo','clippy','--offline','--locked','--all-targets','--','-D','warnings'],['cargo','test','--offline','--locked','-p','knotrel-core' if repo==core else 'knotrel-benchmarks'],['cargo','doc','--offline','--locked','--no-deps']]):
  with (H/f'{repo.name}-check-{i}.txt').open('w') as log:r=subprocess.run(cmd,cwd=repo,env=dict(os.environ,RUSTDOCFLAGS='-D warnings'),stdout=log,stderr=log)
  checks.append({'repo':repo.name,'command':cmd,'exit_code':r.returncode})
m['checks']=checks;m['artifact_sha256']={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in H.iterdir() if p.is_file()}
(H/'manifest.json').write_text(json.dumps(m,indent=2)+'\n');assert all(c['exit_code']==0 for c in checks)
print('Locality traces and checks completed')
