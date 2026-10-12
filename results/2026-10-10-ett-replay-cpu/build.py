"""Build isolated replay CPU diagnostics; never modify production checkouts."""
import hashlib,json,shutil,subprocess,tempfile,os
from pathlib import Path
H=Path(__file__).resolve().parent;P=H.parent/'2026-10-10-ett-scan-root'
b=json.loads((P/'builds.json').read_text());old=Path(b['workspace'])
w=Path(tempfile.mkdtemp(prefix='knotrel-replay-cpu-'))
for repo in ('knotrel','knotrel-benchmarks'):
 shutil.copytree(old/repo,w/repo,ignore=shutil.ignore_patterns('target','.git','results','__pycache__'))
bench=w/'knotrel-benchmarks';core=w/'knotrel'
p=bench/'crates/knotrel-benchmarks/Cargo.toml'
s=p.read_text().replace('[dependencies]','[dependencies]\nrustix = { version = "=1.1.4", features = ["time"] }');p.write_text(s)
p=bench/'crates/knotrel-benchmarks/src/main.rs';s=p.read_text()
s=s.replace('    workload_wall_ns: u128,','    workload_wall_ns: u128,\n    replay_thread_cpu_ns: u128,\n    replay_process_cpu_ns: u128,')
s=s.replace('    let wall_start = Instant::now();','    let process_cpu_start = replay_cpu_ns(rustix::time::ClockId::ProcessCPUTime);\n    let thread_cpu_start = replay_cpu_ns(rustix::time::ClockId::ThreadCPUTime);\n    let wall_start = Instant::now();')
s=s.replace('    let workload_wall_ns = wall_start.elapsed().as_nanos();','    let workload_wall_ns = wall_start.elapsed().as_nanos();\n    let replay_thread_cpu_ns = replay_cpu_ns(rustix::time::ClockId::ThreadCPUTime) - thread_cpu_start;\n    let replay_process_cpu_ns = replay_cpu_ns(rustix::time::ClockId::ProcessCPUTime) - process_cpu_start;')
s=s.replace('        workload_wall_ns,','        workload_wall_ns,\n        replay_thread_cpu_ns,\n        replay_process_cpu_ns,')
s+='\n/// Reads a CPU clock in nanoseconds for the isolated replay diagnostic.\nfn replay_cpu_ns(clock: rustix::time::ClockId) -> u128 {\n    let t = rustix::time::clock_gettime(clock);\n    u128::try_from(t.tv_sec).expect("nonnegative CPU seconds") * 1_000_000_000\n        + u128::try_from(t.tv_nsec).expect("nonnegative CPU nanoseconds")\n}\n'
p.write_text(s)
subprocess.run(['cargo','fmt','--all'],cwd=bench,check=True)
meta={'workspace':str(w),'variants':{},'pilot_builds_sha256':hashlib.sha256((P/'builds.json').read_bytes()).hexdigest()}
for v in ('before','after'):
 for name in ('forest','dynamic'):(core/f'crates/knotrel-core/src/{name}.rs').write_bytes((P/f'{v}-{name}.rs.txt').read_bytes())
 with (H/f'{v}-build.txt').open('w') as log:subprocess.run(['cargo','build','--offline','--release','--bin','knotrel-benchmarks'],cwd=bench,stdout=log,stderr=log,check=True)
 binary=w/v;shutil.copy2(bench/'target/release/knotrel-benchmarks',binary)
 meta['variants'][v]={'binary':str(binary),'binary_sha256':hashlib.sha256(binary.read_bytes()).hexdigest()}
for name in ('Cargo.lock','crates/knotrel-benchmarks/Cargo.toml','crates/knotrel-benchmarks/src/main.rs'):(H/(Path(name).name+'.txt')).write_bytes((bench/name).read_bytes())
(H/'builds.json').write_text(json.dumps(meta,indent=2)+'\n')
checks=[['cargo','fmt','--all','--','--check'],['cargo','clippy','--offline','--locked','--workspace','--all-targets','--','-D','warnings'],['cargo','test','--offline','--locked','--workspace'],['cargo','doc','--offline','--locked','--workspace','--no-deps']]
for i,cmd in enumerate(checks):
 with (H/f'verify-{i}.txt').open('w') as log:subprocess.run(cmd,cwd=bench,env=dict(os.environ,RUSTDOCFLAGS='-D warnings'),stdout=log,stderr=log,check=True)
(H/'verification.json').write_text(json.dumps({'all_passed':True,'commands':checks},indent=2)+'\n')
print(w)
