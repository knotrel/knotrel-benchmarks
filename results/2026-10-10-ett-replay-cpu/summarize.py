"""Summarize replay-local CPU evidence; preserve signed boundary discrepancies."""
import json,statistics
from pathlib import Path
H=Path(__file__).resolve().parent
x=json.loads((H/'comparison.json').read_text());e=json.loads((H/'environment.json').read_text())
assert e['no_sleep_observed'] and e['collector_exit_code']==0
assert not x['failed'] and all(r['complete'] for r in x['rows'])
rows=[]
for r in x['rows']:
 pairs=[]
 for p in r['pairs']:
  a,b=p['values']['after'],p['values']['before']
  cpu=100*(a['thread_cpu_ns']/b['thread_cpu_ns']-1)
  pairs.append({'trial':p['trial'],'wall_change_percent':p['runtime_change_percent'],'thread_cpu_change_percent':cpu,'same_direction':(cpu<0)==(p['runtime_change_percent']<0)})
 rows.append({'reference':r['reference'],'pairs':pairs,'gap_percent':{v:{'median':statistics.median(100*p['values'][v]['wall_minus_thread_ns']/p['values'][v]['runtime_ns'] for p in r['pairs']),'max':max(100*p['values'][v]['wall_minus_thread_ns']/p['values'][v]['runtime_ns'] for p in r['pairs'])} for v in ('before','after')}})
(H/'cpu-summary.json').write_text(json.dumps({'rows':rows,'same_direction_pairs':sum(p['same_direction'] for r in rows for p in r['pairs'])},indent=2)+'\n')
print('Same-direction wall/CPU pairs:',sum(p['same_direction'] for r in rows for p in r['pairs']))
