"""Reconstruct baseline and add phase-boundary observation to an isolated runner."""
import difflib,hashlib,json,shutil,subprocess,tempfile,sys
from pathlib import Path
H=Path(__file__).resolve().parent;ROOT=H.parents[1];CORE=ROOT.parent/'knotrel';sys.path.insert(0,str(ROOT/'scripts'))
from run_baseline import hashes
ref=json.loads((H.parent/'2026-10-07-hdt-promotion-joins/builds.json').read_text());assert hashes()==ref['original_source_sha256']
work=Path(tempfile.mkdtemp(prefix='knotrel-phase-resources-',dir='/private/tmp'))
for source in (ROOT,CORE):
 dest=work/source.name;dest.mkdir()
 for n in ('Cargo.toml','Cargo.lock','rust-toolchain.toml'):(dest/n).write_bytes((source/n).read_bytes())
 shutil.copytree(source/'crates',dest/'crates')
p=work/ROOT.name/'crates/knotrel-benchmarks/src/main.rs';before=p.read_text();s=before
helper='''
/// Isolated external observation point; outside original operation timers.
fn phase_marker(name: &str) {
    eprintln!("KNOTREL_PHASE {name}");
    let mut ack = String::new();
    std::io::stdin().read_line(&mut ack).expect("observer acknowledgement");
    assert_eq!(ack, "ok\\n", "observer disconnected");
}
'''
s=s.replace('fn replay( ', 'fn replay( ') # No-op anchor; replacements below are checked.
for needle,replacement in [
 ('    let setup_start = Instant::now();','    phase_marker("empty_before_start");\n    phase_marker("empty_before_end");\n    phase_marker("setup_start");\n    let setup_start = Instant::now();'),
 ('    let setup_ns = setup_start.elapsed().as_nanos();','    let setup_ns = setup_start.elapsed().as_nanos();\n    phase_marker("setup_end");'),
 ('    let wall_start = Instant::now();','    phase_marker("replay_start");\n    let wall_start = Instant::now();'),
 ('    let workload_wall_ns = wall_start.elapsed().as_nanos();','    let workload_wall_ns = wall_start.elapsed().as_nanos();\n    phase_marker("replay_end");\n    phase_marker("empty_after_start");\n    phase_marker("empty_after_end");')]:
 assert s.count(needle)==1;s=s.replace(needle,replacement)
p.write_text(s+helper);subprocess.run(['cargo','fmt','--all'],cwd=work/ROOT.name,check=True);after=p.read_text()
(H/'before-main.rs.txt').write_text(before);(H/'after-main.rs.txt').write_text(after)
(H/'diagnostic.patch').write_text(''.join(difflib.unified_diff(before.splitlines(True),after.splitlines(True),fromfile='a/crates/knotrel-benchmarks/src/main.rs',tofile='b/crates/knotrel-benchmarks/src/main.rs')))
r=subprocess.run(['cargo','build','--release','--locked','--bin','knotrel-benchmarks'],cwd=work/ROOT.name,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT);(H/'build-log.txt').write_text(r.stdout);r.check_returncode()
binary=work/ROOT.name/'target/release/knotrel-benchmarks'
(H/'builds.json').write_text(json.dumps({'workspace':str(work),'binary':str(binary),'binary_sha256':hashlib.sha256(binary.read_bytes()).hexdigest(),'original_source_sha256':ref['original_source_sha256'],'diagnostic_source_sha256':hashlib.sha256(after.encode()).hexdigest(),'compiler':subprocess.check_output(['rustc','-vV'],text=True)},indent=2)+'\n')
print(work)
