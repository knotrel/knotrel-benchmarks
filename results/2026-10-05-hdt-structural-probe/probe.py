"""Compile isolated, instrumented core snapshots; never time their execution."""
import hashlib,json,pathlib,shutil,subprocess,tempfile
HERE=pathlib.Path(__file__).resolve().parent
ROOT=HERE.parents[1];CORE=ROOT.parent/'knotrel'
assert not (HERE/'results.json').exists(), 'preserve existing measurements'
manifest=json.loads((ROOT/'results/2026-10-05-hdt-joins/manifest.json').read_text())
trace_path=next((ROOT/'results/2026-10-05-hdt-path-investigation').glob('*.trace.json'))
trace_bytes=trace_path.read_bytes();trace=json.loads(trace_bytes)
work=pathlib.Path(tempfile.mkdtemp(prefix='knotrel-structural-'))
lines=[f"node {i} 0 0" for i in range(trace['config']['nodes'])]
lines += [f'initial {a} {b} 1' for a,b in trace['trace']['initial_edges']]
lines += [f"{o['op']} {o['source']} {o['target']} {int(o.get('expected',True))}" for o in trace['trace']['operations']]
(work/'trace.txt').write_text('\n'.join(lines)+'\n')
new='''        // The new directed tokens are pivots: preserve the tour sequence
        // left, ab, right, ba without splitting tours to recover pivots.
        // Both joins retain AVL balance and O(log V) worst-case link cost.
        let tour = self.join(left, ab, right);
        self.join(Some(tour), ba, None);'''
old='''        let left = self.concat(left, Some(ab));
        let left = self.concat(left, right);
        self.concat(left, Some(ba));'''
harness=r'''
use knotrel_core::{HdtGraph, diagnostic_counts};
fn main() {
 let input=std::fs::read_to_string(std::env::args().nth(1).unwrap()).unwrap();
 let mut graph=HdtGraph::new(); let mut totals=[[0u64;7];5]; let mut calls=[0u64;5];
 for line in input.lines() {
  let p:Vec<_>=line.split_whitespace().collect();
  let a=p[1].parse().unwrap();let b=p[2].parse().unwrap();
  diagnostic_counts();
  let group=match p[0] {
   "node"=>{assert!(graph.add_node(a));0},
   "initial"=>{assert!(graph.link(a,b).unwrap());1},
   "cut"=>{assert!(graph.cut(a,b).unwrap());2},
   "link"=>{assert!(graph.link(a,b).unwrap());3},
   "connected"=>{assert_eq!(graph.connected(a,b).unwrap(),p[3]=="1");4},
   _=>panic!("unknown operation")
  };
  let values=diagnostic_counts();calls[group]+=1;
  for i in 0..7 {totals[group][i]+=values[i];}
 }
 for group in 0..5 {println!("{} {} {:?}",group,calls[group],totals[group]);}
}
'''
(work/'main.rs').write_text(harness)
result={}
commands=[]
for variant in ['before','after']:
 src=work/variant;shutil.copytree(CORE/'crates/knotrel-core/src',src)
 forest=src/'hdt_forest.rs';s=forest.read_text()
 if variant=='before':assert new in s;s=s.replace(new,old)
 expected=manifest['variants'][variant]['source_sha256']['core/crates/knotrel-core/src/hdt_forest.rs']
 assert hashlib.sha256(s.encode()).hexdigest()==expected,'forest differs from measured version'
 for path in src.glob('*.rs'):
  if path.name!='hdt_forest.rs':
   assert hashlib.sha256(path.read_bytes()).hexdigest()==manifest['variants'][variant]['source_sha256']['core/crates/knotrel-core/src/'+path.name]
 for index,signature in enumerate(['fn pull(&mut self, i: usize) {','fn join(&mut self, left: Option<usize>, pivot: usize, right: Option<usize>) -> usize {','fn split(&mut self, root: Option<usize>, k: usize) -> (Option<usize>, Option<usize>) {','fn root(&self, mut i: usize) -> usize {','fn rank(&self, mut i: usize) -> usize {']):
  assert s.count(signature)==1
  s=s.replace(signature,signature+f'\n        crate::DIAGNOSTIC[{index}].fetch_add(1, std::sync::atomic::Ordering::Relaxed);')
 for name,index in [('root',5),('rank',6)]:
  start=s.index(f'fn {name}(');end=s.index('\n    fn ',start+1)
  part=s[start:end];needle='while let Some(parent) = self.tokens[i].parent {'
  assert part.count(needle)==1
  s=s[:start]+part.replace(needle,needle+f'\n            crate::DIAGNOSTIC[{index}].fetch_add(1, std::sync::atomic::Ordering::Relaxed);')+s[end:]
 forest.write_text(s)
 with (src/'lib.rs').open('a') as f:f.write('''
static DIAGNOSTIC: [std::sync::atomic::AtomicU64;7] = [const { std::sync::atomic::AtomicU64::new(0) };7];
/// Diagnostic-only destructive counter snapshot, absent from production sources.
pub fn diagnostic_counts() -> [u64;7] { std::array::from_fn(|i| DIAGNOSTIC[i].swap(0,std::sync::atomic::Ordering::Relaxed)) }
''')
 lib=work/f'lib{variant}.rlib';exe=work/f'probe-{variant}'
 for cmd in [['rustc','--edition=2024','--crate-type=rlib','--crate-name=knotrel_core','-O',str(src/'lib.rs'),'-o',str(lib)],['rustc','--edition=2024','-O',str(work/'main.rs'),'--extern',f'knotrel_core={lib}','-o',str(exe)]]:
  subprocess.run(cmd,check=True);commands.append(cmd)
 outputs=[subprocess.check_output([str(exe),str(work/'trace.txt')],text=True) for _ in range(2)]
 assert outputs[0]==outputs[1],'counts must be deterministic'
 result[variant]={}
 for line in outputs[0].splitlines():
  group,count,values=line.split(' ',2)
  result[variant][['registration','initial_links','cut','link','connected'][int(group)]]={'operations':int(count),'counts':dict(zip(['pull','join','split','root_calls','rank_calls','root_parent_steps','rank_parent_steps'],json.loads(values)))}
 (HERE/(variant+'-instrumented-forest.rs.txt')).write_text(s)
(HERE/'harness.rs.txt').write_text(harness)
(HERE/'results.json').write_text(json.dumps({'scope':'Deterministic diagnostic counts only; no timing claims','source_variants':manifest['variants'],'compiler':subprocess.check_output(['rustc','-vV'],text=True),'trace_reference':str(trace_path.relative_to(ROOT)),'trace_sha256':hashlib.sha256(trace_bytes).hexdigest(),'commands':commands,'repeated_identical_runs_per_variant':2,'results':result},indent=2)+'\n')
print(json.dumps(result,indent=2))
