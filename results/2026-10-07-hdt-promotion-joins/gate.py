"""Apply the predeclared pilot gate without changing thresholds after measurement."""
import json
from pathlib import Path
H=Path(__file__).resolve().parent;d=json.loads((H/'comparison.json').read_text());rows=d['rows']
assert len(rows)==9
blocks=[r for r in rows if r['workload']=='sustained-churn-blocks-v1']
controls=[r for r in rows if r not in blocks]
qualified=[r for r in blocks if r['complete'] and r['metrics']['runtime_ns']['delta_percent']<=-3 and r['pairs_faster']>=3]
regressions=[r for r in controls if r['complete'] and r['metrics']['runtime_ns']['delta_percent']>5 and sum(p['runtime_delta_percent']>0 for p in r['pairs'])>=3]
passed=not d['failed'] and all(r['complete'] for r in rows) and len(qualified)>=3 and not regressions
result={'passed':passed,'qualifying_blocks':len(qualified),'required_blocks':3,'control_regressions':regressions,'scope':'Engineering screening gate, not statistical significance; no threshold tuning.'}
(H/'gate.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
