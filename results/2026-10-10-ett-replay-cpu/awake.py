"""Capture environmental validity around one fixed-budget collection."""
import datetime,json,re,subprocess,sys
from pathlib import Path
H=Path(__file__).resolve().parent
now=lambda:datetime.datetime.now(datetime.timezone.utc)
start=now()
a=subprocess.run(['pmset','-g','assertions'],capture_output=True,text=True,check=True)
(H/'power-assertions-start.txt').write_text(a.stdout)
assert 'caffeinate' in a.stdout and 'PreventUserIdleSystemSleep' in a.stdout
r=subprocess.run([sys.executable,str(H/'collect.py')])
end=now()
after=subprocess.run(['pmset','-g','assertions'],capture_output=True,text=True,check=True)
(H/'power-assertions-end.txt').write_text(after.stdout)
power=subprocess.run(['pmset','-g','log'],capture_output=True,text=True,check=True)
events=[];previous=None
for line in power.stdout.splitlines():
 m=re.match(r'^(\d{4}-\d\d-\d\d \d\d:\d\d:\d\d [+-]\d{4})\s+(Sleep|Wake|DarkWake)\s',line)
 if not m:continue
 dt=datetime.datetime.strptime(m[1],'%Y-%m-%d %H:%M:%S %z')
 event={'timestamp':dt.isoformat(),'kind':m[2],'line':line}
 if dt<start.replace(microsecond=0):previous=event
 elif dt<=end:events.append(event)
(H/'power-events.txt').write_text('\n'.join(e['line'] for e in events)+'\n')
active='caffeinate' in after.stdout
valid=active and not any(e['kind']=='Sleep' for e in events)
(H/'environment.json').write_text(json.dumps({'start_utc':start.isoformat(),'end_utc':end.isoformat(),'collector_exit_code':r.returncode,'assertion_present_at_end':active,'preceding_power_event':previous,'events':events,'no_sleep_observed':valid,'limitation':'No observed sleep is an environmental check, not a guarantee of CPU isolation or equal cache state.'},indent=2)+'\n')
sys.exit(r.returncode)
