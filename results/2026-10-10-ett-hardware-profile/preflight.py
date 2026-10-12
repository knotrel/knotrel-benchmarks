"""Read-only profiler and frozen-binary readiness check; never change Xcode selection."""
import datetime,hashlib,json,os,subprocess,sys
from pathlib import Path
H=Path(__file__).resolve().parent
pilot=H.parent/'2026-10-10-ett-scan-root'
b=json.loads((pilot/'builds.json').read_text())
report={'checked_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'binaries':{},'tools':[]}
for variant,meta in b['variants'].items():
 p=Path(meta['binary']);exists=p.is_file()
 report['binaries'][variant]={'path':str(p),'present':exists,'hash_matches':exists and hashlib.sha256(p.read_bytes()).hexdigest()==meta['binary_sha256']}
envs=[('selected',dict(os.environ))]
for root in (Path('/Applications'),Path.home()/'Applications'):
 if root.is_dir():
  for app in root.glob('Xcode*.app'):
   developer=app/'Contents/Developer'
   if developer.is_dir():envs.append((str(developer),dict(os.environ,DEVELOPER_DIR=str(developer))))
for name,env in envs:
 r=subprocess.run(['xcrun','xctrace','list','templates'],env=env,capture_output=True,text=True,timeout=30)
 report['tools'].append({'developer':name,'exit_code':r.returncode,'stdout':r.stdout,'stderr':r.stderr})
report['profiler_ready']=any(x['exit_code']==0 for x in report['tools'])
report['frozen_binaries_ready']=all(x['hash_matches'] for x in report['binaries'].values())
report['ready']=report['profiler_ready'] and report['frozen_binaries_ready']
(H/'readiness.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({'profiler_ready':report['profiler_ready'],'frozen_binaries_ready':report['frozen_binaries_ready'],'ready':report['ready']},indent=2))
sys.exit(0 if report['ready'] else 2)
