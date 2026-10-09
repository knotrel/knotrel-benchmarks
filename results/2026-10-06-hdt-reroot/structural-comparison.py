"""Compare deterministic forest work, never infer runtime from call counts."""
import json
from pathlib import Path
H=Path(__file__).resolve().parent
b=json.loads((H.parent/'2026-10-06-hdt-reroot-probe/results.json').read_text())
a=json.loads((H.parent/'2026-10-06-hdt-reroot-candidate-probe/results.json').read_text())
rows=[]
for before,after in zip(b['results'],a['results'],strict=True):
 assert all(before[k]==after[k] for k in ('nodes','workload','query_percent','trace_fingerprint_fnv1a64','trace_sha256','promotions_by_source_level'))
 changes={}
 for scope,values in before['counts'].items():
  changes[scope]={k:{'before':v,'after':after['counts'][scope][k],'delta_percent':None if v==0 else 100*(after['counts'][scope][k]/v-1)} for k,v in values.items()}
 rows.append({k:before[k] for k in ('nodes','workload','query_percent')}|{'changes':changes})
(H/'structural-comparison.json').write_text(json.dumps({'scope':'Two identical replays per variant per trace; function-entry counts are not timing shares. Promotions by level are unchanged.','rows':rows},indent=2)+'\n')
for r in rows:
 print(r['nodes'],r['workload'],{k:v['delta_percent'] for k,v in r['changes']['promote_tree'].items() if k in ('pull','join','split')})
