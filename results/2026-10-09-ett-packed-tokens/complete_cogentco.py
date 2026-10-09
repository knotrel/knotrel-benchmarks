"""Complete only missing-input cases, preserving all original failures."""
import hashlib,json,sys
from pathlib import Path
H=Path(__file__).resolve().parent;ROOT=H.parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from run_scale import run_measurement,peak_rss
m=json.loads((H/'manifest.json').read_text());trace=json.loads((H/'recovered-trace.json').read_text())
assert hashlib.sha256(Path(trace['path']).read_bytes()).hexdigest()==trace['sha256']
assert not (H/'completed-manifest.json').exists()
for c in m['cases']:
 if c['exit_code']==0:continue
 assert c['family']=='cogentco'
 c['original_failed_name']=c['name'];c['name']+='-recovered';cmd=c['command'].copy();cmd[cmd.index('--trace-in')+1]=trace['path']
 b=m['builds']['variants'][c['variant']];assert hashlib.sha256(Path(b['binary']).read_bytes()).hexdigest()==b['binary_sha256']
 r,timeout=run_measurement(cmd,120);(H/(c['name']+'.stderr.txt')).write_text(r.stderr);(H/(c['name']+'.json')).write_text(r.stdout)
 c.update(command=cmd,exit_code=r.returncode,timed_out=timeout,rss_bytes=peak_rss(r.stderr,sys.platform));assert r.returncode==0
m['completion_note']='Original manifest retains 16 missing-file failures. Only those cases repeated, same byte-identical trace and original balanced order, collected after synthetic cases.'
m['artifact_sha256'].update({p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in H.glob('*-recovered.*')})
(H/'completed-manifest.json').write_text(json.dumps(m,indent=2)+'\n')
