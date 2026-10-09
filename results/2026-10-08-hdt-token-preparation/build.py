"""Build one isolated diagnostic binary with none/read/write preparation modes."""
import difflib,hashlib,json,shutil,subprocess,tempfile,sys
from pathlib import Path
H=Path(__file__).resolve().parent;ROOT=H.parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from run_baseline import hashes
base=json.loads((H.parent/'2026-10-08-hdt-phase-resources/builds.json').read_text());assert hashes()==base['original_source_sha256'];old=Path(base['workspace'])
work=Path(tempfile.mkdtemp(prefix='knotrel-token-prep-',dir='/private/tmp'))
for name in ('knotrel','knotrel-benchmarks'):
 dest=work/name;dest.mkdir()
 for f in ('Cargo.toml','Cargo.lock','rust-toolchain.toml'):(dest/f).write_bytes((old/name/f).read_bytes())
 shutil.copytree(old/name/'crates',dest/'crates')
paths={'forest':work/'knotrel/crates/knotrel-core/src/hdt_forest.rs','hdt':work/'knotrel/crates/knotrel-core/src/hdt.rs','engines':work/'knotrel-benchmarks/crates/knotrel-benchmarks/src/engines.rs','main':work/'knotrel-benchmarks/crates/knotrel-benchmarks/src/main.rs'}
before={k:p.read_text() for k,p in paths.items()}
s=before['forest'];needle='impl Forest {';assert s.count(needle)==1;s=s.replace(needle,needle+'''
    /// Diagnostic: touch initialized token pages without changing their fields.
    /// O(number of tokens); intentionally perturbs cache and writable-page state.
    pub(crate) fn diagnostic_touch_tokens(&mut self, write: bool) -> usize {
        for token in &mut self.tokens {
            let value = std::hint::black_box(token.candidate);
            if write {
                token.candidate = value;
            }
        }
        self.tokens.len()
    }
''');paths['forest'].write_text(s+'\n'+(H/'token-test.rs.txt').read_text())
s=before['hdt'];needle='impl HdtGraph {';assert s.count(needle)==1;s=s.replace(needle,needle+'''
    /// Diagnostic-only initialized-token preparation; preserves graph semantics.
    /// Visits every forest arena in O(total tokens); does not touch all graph storage.
    pub fn diagnostic_touch_tokens(&mut self, write: bool) -> usize {
        self.levels.iter_mut().map(|level| level.forest.diagnostic_touch_tokens(write)).sum()
    }
''');paths['hdt'].write_text(s)
s=before['engines'];needle='impl Engine {';assert s.count(needle)==1;s=s.replace(needle,needle+'''
    /// Isolated HDT token-arena diagnostic, preserving graph state.
    pub fn diagnostic_touch_tokens(&mut self, write: bool) -> usize {
        match &mut self.storage {
            Storage::Hdt(graph) => graph.diagnostic_touch_tokens(write),
            _ => panic!("preparation diagnostic requires HDT"),
        }
    }
''');paths['engines'].write_text(s)
s=before['main'];needle='struct Run {';s=s.replace(needle,needle+'\n    preparation_ns: u128,\n    prepared_tokens: usize,\n    preparation_mode: String,')
needle='    phase_marker("replay_start");';assert s.count(needle)==1;s=s.replace(needle,'''
    let preparation_mode = std::env::var("KNOTREL_DIAGNOSTIC_PREPARATION").unwrap_or_else(|_| "none".into());
    assert!(matches!(preparation_mode.as_str(), "none" | "read" | "write"));
    phase_marker("preparation_start");
    let preparation_start = Instant::now();
    let prepared_tokens = match preparation_mode.as_str() {
        "read" => graph.diagnostic_touch_tokens(false),
        "write" => graph.diagnostic_touch_tokens(true),
        _ => 0,
    };
    let preparation_ns = preparation_start.elapsed().as_nanos();
    phase_marker("preparation_end");
'''+needle)
s=s.replace('    Ok(Run {','    Ok(Run {\n        preparation_ns,\n        prepared_tokens,\n        preparation_mode,');paths['main'].write_text(s)
subprocess.run(['cargo','fmt','--all'],cwd=work/'knotrel',check=True);subprocess.run(['cargo','fmt','--all'],cwd=work/'knotrel-benchmarks',check=True)
patch=''
for k,p in paths.items():
 after=p.read_text();rel=str(p.relative_to(work));(H/(k+'-before.rs.txt')).write_text(before[k]);(H/(k+'-after.rs.txt')).write_text(after)
 patch+=''.join(difflib.unified_diff(before[k].splitlines(True),after.splitlines(True),fromfile='a/'+rel,tofile='b/'+rel))
(H/'diagnostic.patch').write_text(patch)
for label,cmd,cwd in [('token-test',['cargo','test','--locked','-p','knotrel-core','preparation_preserves_all_token_fields_and_recycled_tours'],work/'knotrel'),('build',['cargo','build','--release','--locked','--bin','knotrel-benchmarks'],work/'knotrel-benchmarks')]:
 r=subprocess.run(cmd,cwd=cwd,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT);(H/(label+'.txt')).write_text(r.stdout);r.check_returncode()
binary=work/'knotrel-benchmarks/target/release/knotrel-benchmarks'
(H/'builds.json').write_text(json.dumps({'workspace':str(work),'binary':str(binary),'binary_sha256':hashlib.sha256(binary.read_bytes()).hexdigest(),'original_source_sha256':base['original_source_sha256'],'parent_diagnostic':str(H.parent/'2026-10-08-hdt-phase-resources'),'source_sha256':{k:hashlib.sha256(p.read_bytes()).hexdigest() for k,p in paths.items()},'compiler':subprocess.check_output(['rustc','-vV'],text=True)},indent=2)+'\n')
print(work)
