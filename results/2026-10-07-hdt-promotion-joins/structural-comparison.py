"""Compare forest work and actual link-side sizes, independently of runtime."""
import json
from pathlib import Path
H=Path(__file__).resolve().parent
b=json.loads((H.parent/'2026-10-07-hdt-promotion-joins-before-probe/results.json').read_text())
a=json.loads((H.parent/'2026-10-07-hdt-promotion-joins-after-probe/results.json').read_text())
rows=[]
for before,after in zip(b['results'],a['results'],strict=True):
 assert all(before[k]==after[k] for k in ('nodes','workload','query_percent','trace_fingerprint_fnv1a64','trace_sha256','promotions_by_source_level'))
 changes={}
 for scope,values in before['counts'].items():
  for k in ('ensure_calls','new_vertex_records','link_calls','right_not_larger','right_singleton','left_singleton'):assert values[k]==after['counts'][scope][k],(scope,k)
  changes[scope]={k:{'before':v,'after':after['counts'][scope][k],'delta_percent':None if v==0 else 100*(after['counts'][scope][k]/v-1)} for k,v in values.items()}
 rows.append({k:before[k] for k in ('nodes','workload','query_percent')}|{'scopes':changes})
(H/'structural-comparison.json').write_text(json.dumps({'scope':'Function-entry counts include recursion, not CPU-time shares. Two identical repeats per variant/trace. Link-side sizes, promotions by level and materialization match.','rows':rows},indent=2)+'\n')
for r in rows:print(r['nodes'],r['scopes']['promote_tree'])
