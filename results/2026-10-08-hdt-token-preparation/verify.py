"""Verify the isolated diagnostic code and preserve every check log."""
import json,subprocess,os
from pathlib import Path
H=Path(__file__).resolve().parent;m=json.loads((H/'builds.json').read_text());cwd=Path(m['workspace'])/'knotrel-benchmarks'
checks=[['cargo','fmt','--all','--','--check'],['cargo','clippy','--locked','--workspace','--all-targets','--','-D','warnings'],['cargo','test','--locked','--workspace','--lib'],['cargo','test','--locked','--workspace','--doc'],['cargo','doc','--locked','--workspace','--no-deps']]
for i,cmd in enumerate(checks):
 env=os.environ.copy()
 if i==4:env['RUSTDOCFLAGS']='-D warnings'
 r=subprocess.run(cmd,cwd=cwd,env=env,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT);(H/f'check-{i}.txt').write_text(r.stdout);r.check_returncode()
core=Path(m['workspace'])/'knotrel'
core_checks=[['cargo','fmt','--all','--','--check'],['cargo','clippy','--locked','-p','knotrel-core','--all-targets','--','-D','warnings'],['cargo','test','--locked','-p','knotrel-core'],['cargo','doc','--locked','-p','knotrel-core','--no-deps']]
for i,cmd in enumerate(core_checks):
 env=os.environ.copy()
 if i==3:env['RUSTDOCFLAGS']='-D warnings'
 r=subprocess.run(cmd,cwd=core,env=env,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT);(H/f'core-check-{i}.txt').write_text(r.stdout);r.check_returncode()
(H/'verification.json').write_text(json.dumps({'all_passed':True,'checks':checks,'core_checks':core_checks,'scope':'Diagnostic harness: format, all-target Clippy, library tests, doctests and Rustdoc. Ordinary CLI tests require the original non-handshake protocol; diagnostic integration is validated by smoke and complete traced replays, not those CLI tests.'},indent=2)+'\n')
print('Diagnostic format, Clippy, library tests/doctests and Rustdoc passed')
