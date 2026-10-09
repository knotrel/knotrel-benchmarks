"""Report replaced work and the added extraction calls, not an instruction-count score."""
import json
from pathlib import Path
H=Path(__file__).resolve().parent
before=json.loads((H.parent/'2026-10-07-hdt-concat-before-probe/results.json').read_text())
after=json.loads((H.parent/'2026-10-07-hdt-concat-after-probe/results.json').read_text())
rows=[]
for b,a in zip(before['results'],after['results'],strict=True):
 assert all(b[k]==a[k] for k in ('nodes','workload','query_percent','trace_fingerprint_fnv1a64','trace_sha256','promotions_by_source_level'))
 changes={}
 for scope,values in b['counts'].items():
  for k in ('ensure_calls','new_vertex_records'):assert values[k]==a['counts'][scope][k]
  changes[scope]={k:{'before':v,'after':a['counts'][scope][k],'delta_percent':None if v==0 else 100*(a['counts'][scope][k]/v-1)} for k,v in values.items()}
 rows.append({k:b[k] for k in ('nodes','workload','query_percent')}|{'scopes':changes})
(H/'structural-comparison.json').write_text(json.dumps({'scope':'Function entries include recursive calls; pop_last adds distinct work. Do not sum unlike calls or infer CPU-time shares. Two deterministic repeats per variant/trace; unchanged promotion levels and endpoint materialization.','rows':rows},indent=2)+'\n')
for r in rows:print(r['nodes'],r['scopes']['promote_tree'])
