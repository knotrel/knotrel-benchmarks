"""Isolated HDT counters; never time these instrumented binaries."""
import hashlib,json,shutil,subprocess,tempfile,sys
from pathlib import Path
H=Path(__file__).resolve().parent;ROOT=H.parents[1];CORE=ROOT.parent/'knotrel'
sys.path.insert(0,str(ROOT/'scripts'))
from run_baseline import hashes
base=json.loads((ROOT/'results/2026-10-06-engine-ranking-sparse/manifest.json').read_text())
assert hashes()==base['source_sha256']
assert not (H/'results.json').exists()
work=Path(tempfile.mkdtemp(prefix='knotrel-blocks-structure-'));src=work/'src';shutil.copytree(CORE/'crates/knotrel-core/src',src)
names=['promote_tree','promote_non_tree','replace_other','outside_replace']
# Scope 0/1 is the promotion body; 2 is other replacement work; 3 is outside repair.
s=(ROOT/'results/2026-10-07-hdt-promotion-joins/before-hdt.rs.txt').read_text()
assert hashlib.sha256(s.encode()).hexdigest()==json.loads((ROOT/'results/2026-10-07-hdt-promotion-joins/builds.json').read_text())['variants']['before']['hdt_sha256']
def insert(signature,code):
 global s
 assert s.count(signature)==1,signature
 s=s.replace(signature,signature+'\n'+code)
insert('fn replace(&mut self, a: usize, b: usize, start: usize) {','let _scope = crate::ProbeScope::enter(2);')
insert('fn promote(&mut self, a: usize, b: usize, i: usize, tree: bool) {','let _scope = crate::ProbeScope::enter(if tree {0} else {1});\ncrate::PROMOTIONS[i*2+usize::from(!tree)].fetch_add(1,std::sync::atomic::Ordering::Relaxed);')
insert('fn ensure(&mut self, v: usize) -> usize {','crate::probe_count(3);')
s=s.replace('        let local = self.tree.len();','        crate::probe_count(4);\n        let local = self.tree.len();')
(src/'hdt.rs').write_text(s);(H/'instrumented-hdt.rs.txt').write_text(s)
s=(ROOT/'results/2026-10-07-hdt-promotion-joins/before-forest.rs.txt').read_text()
assert hashlib.sha256(s.encode()).hexdigest()==json.loads((ROOT/'results/2026-10-07-hdt-promotion-joins/builds.json').read_text())['variants']['before']['forest_sha256']
for i,sig in enumerate(['fn pull(&mut self, i: usize) {','fn join(&mut self, left: Option<usize>, pivot: usize, right: Option<usize>) -> usize {','fn split(&mut self, root: Option<usize>, k: usize) -> (Option<usize>, Option<usize>) {']):
 assert s.count(sig)==1;s=s.replace(sig,sig+f'\n crate::probe_count({i});')
needle='        let right = self.reroot(self.vertex_tokens[b]);'
assert s.count(needle)==1
s=s.replace(needle,needle+'\n crate::probe_count(5);\n if self.size(right) <= self.size(left) { crate::probe_count(6); }\n if self.size(right) == 1 { crate::probe_count(7); }\n if self.size(left) == 1 { crate::probe_count(8); }')
(src/'hdt_forest.rs').write_text(s);(H/'instrumented-forest.rs.txt').write_text(s)
extra='''
static SCOPE: std::sync::atomic::AtomicUsize = std::sync::atomic::AtomicUsize::new(3);
static COUNTS: [std::sync::atomic::AtomicU64;36] = [const {std::sync::atomic::AtomicU64::new(0)};36];
static PROMOTIONS: [std::sync::atomic::AtomicU64;128] = [const {std::sync::atomic::AtomicU64::new(0)};128];
fn probe_count(index:usize) {COUNTS[SCOPE.load(std::sync::atomic::Ordering::Relaxed)*9+index].fetch_add(1,std::sync::atomic::Ordering::Relaxed);}
struct ProbeScope(usize);
impl ProbeScope { fn enter(scope:usize)->Self {Self(SCOPE.swap(scope,std::sync::atomic::Ordering::Relaxed))} }
impl Drop for ProbeScope {fn drop(&mut self) {SCOPE.store(self.0,std::sync::atomic::Ordering::Relaxed);}}
/// Isolated diagnostic snapshot, not part of the production API.
pub fn probe_reset()->([u64;36],[u64;128]) {(std::array::from_fn(|i|COUNTS[i].swap(0,std::sync::atomic::Ordering::Relaxed)),std::array::from_fn(|i|PROMOTIONS[i].swap(0,std::sync::atomic::Ordering::Relaxed)))}
'''
with (src/'lib.rs').open('a') as f:f.write(extra)
(H/'instrumentation.rs.txt').write_text(extra)
harness='''
use knotrel_core::{HdtGraph,probe_reset};
use std::io::BufRead;
fn main(){
 let input=std::io::BufReader::new(std::fs::File::open(std::env::args().nth(1).unwrap()).unwrap());
 let mut g=HdtGraph::new();let mut began=false;
 for line in input.lines(){let line=line.unwrap();let p:Vec<_>=line.split_whitespace().collect();
 if p[0]=="replay"{probe_reset();g.reset_stats();began=true;continue;}
 let a=p[1].parse().unwrap();let b=p[2].parse().unwrap();
 match p[0]{"node"=>{assert!(g.add_node(a));},"initial"|"link"=>{assert!(g.link(a,b).unwrap());},"cut"=>{assert!(g.cut(a,b).unwrap());},"connected"=>assert_eq!(g.connected(a,b).unwrap(),p[3]=="1"),_=>panic!()}
 }
 assert!(began);let (a,b)=probe_reset();println!("{:?}",a);println!("{:?}",b);
 let s=g.stats();println!("[{}, {}, {}, {}, {}, {}]",s.tree_cuts,s.candidate_edges,s.replacements,s.tree_promotions,s.non_tree_promotions,s.levels_visited);
}
'''
(work/'main.rs').write_text(harness);(H/'harness.rs.txt').write_text(harness)
lib=work/'libknotrel_core.rlib';exe=work/'probe'
commands=[['rustc','--edition=2024','--crate-type=rlib','--crate-name=knotrel_core','-O',str(src/'lib.rs'),'-o',str(lib)],['rustc','--edition=2024','-O',str(work/'main.rs'),'--extern',f'knotrel_core={lib}','-o',str(exe)]]
for cmd in commands:subprocess.run(cmd,check=True)
results=[]
for n in (100000,1000000):
 for workload in ('sustained-churn-blocks-v1',):
  trace=work/'trace.json';trace.unlink(missing_ok=True)
  cmd=[str(ROOT/'target/release/knotrel-benchmarks'),'--engine','compact-bfs','--nodes',str(n),'--rounds','10','--seed','42','--query-percent','90','--workload',workload,'--warmup','0','--repetitions','1','--trace-out',str(trace)]
  report=json.loads(subprocess.check_output(cmd,text=True));t=json.loads(trace.read_text())
  ref=next(c for c in base['cases'] if c['nodes']==n and c['query_percent']==90 and c['workload']==workload and c['engine']=='hdt')
  old=json.loads((ROOT/'results/2026-10-06-engine-ranking-sparse'/(ref['name']+'.json')).read_text())
  assert report['trace_fingerprint_fnv1a64']==old['trace_fingerprint_fnv1a64']
  with (work/'trace.txt').open('w') as f:
   for i in range(n):f.write(f'node {i} 0 0\n')
   for a,b in t['trace']['initial_edges']:f.write(f'initial {a} {b} 1\n')
   f.write('replay\n')
   for op in t['trace']['operations']:f.write(f"{op['op']} {op['source']} {op['target']} {int(op.get('expected',True))}\n")
  outputs=[subprocess.check_output([str(exe),str(work/'trace.txt')],text=True) for _ in range(2)]
  assert outputs[0]==outputs[1]
  values,promotions,stats=map(json.loads,outputs[0].splitlines())
  diagnostic=json.loads((ROOT/'results/2026-10-06-hdt-blocks-profile'/f'{workload}-n{n}-q90-p0.json').read_text())
  assert stats==[diagnostic['counters'][k] for k in ['tree_cuts','candidate_edges','replacements','tree_promotions','non_tree_promotions','levels_visited']]
  assert sum(promotions[::2])==stats[3] and sum(promotions[1::2])==stats[4]
  results.append({'nodes':n,'workload':workload,'query_percent':90,'trace_fingerprint_fnv1a64':report['trace_fingerprint_fnv1a64'],'trace_sha256':hashlib.sha256(trace.read_bytes()).hexdigest(),'export_command':cmd,'counts':{scope:dict(zip(['pull','join','split','ensure_calls','new_vertex_records','link_calls','right_not_larger','right_singleton','left_singleton'],values[i*9:(i+1)*9])) for i,scope in enumerate(names)},'promotions_by_source_level':{str(i):{'tree':promotions[2*i],'non_tree':promotions[2*i+1]} for i in range(64) if any(promotions[2*i:2*i+2])}})
  print(n,workload,flush=True)
assert hashes()==base['source_sha256']
(H/'results.json').write_text(json.dumps({'scope':'Deterministic operation counts only, no timings. Two identical runs per trace. Source-level promotion counts. New vertex records are materialization counts, not allocator calls or bytes.','source_sha256':base['source_sha256'],'compiler':subprocess.check_output(['rustc','-vV'],text=True),'commands':commands,'results':results},indent=2)+'\n')
