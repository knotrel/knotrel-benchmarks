"""Recover pinned input and require byte-identical historical trace."""
import hashlib,json,subprocess,tempfile,urllib.request
from pathlib import Path
H=Path(__file__).resolve().parent
m=json.loads((H.parent/'2026-10-04-cogentco-campaign/manifest.json').read_text());p=m['provenance'];t=m['transform']
w=Path(tempfile.mkdtemp(prefix='knotrel-ett-cogentco-',dir='/private/tmp'));raw=urllib.request.urlopen(p['source_url'],timeout=30).read()
assert hashlib.sha256(raw).hexdigest()==p['source_sha256']
f=w/'Cogentco.graphml';f.write_bytes(raw);out=w/'cogentco.trace.json'
cmd=['python3',str(H.parent/'2026-10-04-cogentco-campaign/import_topology_zoo.py'),str(f),'--output',str(out),'--sha256',p['source_sha256'],'--failures',str(t['failures']),'--seed',str(t['seed'])]
for k in ('source_url','source_revision','retrieved_date','license','citation'):cmd+=['--'+k.replace('_','-'),p[k]]
subprocess.run(cmd,check=True)
assert hashlib.sha256(out.read_bytes()).hexdigest()==m['trace_sha256']
(H/'recovered-trace.json').write_text(json.dumps({'path':str(out),'sha256':m['trace_sha256'],'source_url':p['source_url'],'historical_trace_identical':True},indent=2)+'\n')
print(out)
