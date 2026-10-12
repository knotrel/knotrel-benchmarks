"""Fixed-budget reproduction using unmodified, hash-checked pilot binaries."""
import datetime, hashlib, json, random, subprocess, sys
from pathlib import Path
H=Path(__file__).resolve().parent
ROOT=H.parents[1]
P=H.parent/'2026-10-10-ett-scan-root'
sys.path.insert(0,str(ROOT/'scripts'))
from run_scale import run_measurement
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
original=json.loads((P/'manifest.json').read_text())
assert not (H/'manifest.json').exists()
selected={}
for c in original['cases']:
    if c['variant']!='before':continue
    if 'sustained-churn-path' in c['name'] or 'dense-bridge' in c['name']:
        selected[c['reference']]=c
assert len(selected)==3
meta={'protocol_sha256':sha(H/'protocol.md'),'pilot_manifest_sha256':sha(P/'manifest.json'),'cases':[],'structural':[]}
probe=json.loads((P/'diagnostic/manifest.json').read_text())
for variant in ('before','after'):
    entry=next(r for r in probe['runs'] if r['variant']==variant)
    binary=Path(entry['command'][0]);assert sha(binary)==entry['binary_sha256']
    for trial in range(2):
        command=[str(binary),'sustained-churn-path-v1','1000000','50']
        r=subprocess.run(command,capture_output=True,text=True,timeout=120)
        name=f'structure-{variant}-{trial}'
        (H/(name+'.json')).write_text(r.stdout);(H/(name+'.stderr.txt')).write_text(r.stderr)
        meta['structural'].append({'name':name,'command':command,'binary_sha256':sha(binary),'exit_code':r.returncode})
        assert r.returncode==0
print('Structural runs complete',flush=True)
groups=[(ref,c,t) for ref,c in selected.items() for t in range(12)]
random.Random(1010).shuffle(groups)
for group,(ref,c,t) in enumerate(groups):
    for variant in (('before','after') if t%2==0 else ('after','before')):
        binary=Path(original['builds']['variants'][variant]['binary'])
        assert sha(binary)==original['builds']['variants'][variant]['binary_sha256']
        command=list(c['command']);command[2]=str(binary)
        name=f'g{group:02d}-t{t:02d}-{variant}'
        started=datetime.datetime.now(datetime.timezone.utc).isoformat()
        r,timeout=run_measurement(command,120)
        (H/(name+'.json')).write_text(r.stdout);(H/(name+'.stderr.txt')).write_text(r.stderr)
        meta['cases'].append({'name':name,'group':group,'trial':t,'variant':variant,'reference':ref,'regime':c['regime'],'command':command,'started_utc':started,'exit_code':r.returncode,'timeout':timeout,'binary_sha256':sha(binary)})
        (H/'manifest.partial.json').write_text(json.dumps(meta,indent=2)+'\n')
    print(f'{group+1}/36 {ref}',flush=True)
meta['artifact_sha256']={p.name:sha(p) for p in H.iterdir() if p.is_file() and p.name!='manifest.partial.json'}
(H/'manifest.json').write_text(json.dumps(meta,indent=2)+'\n')
(H/'manifest.partial.json').unlink()
