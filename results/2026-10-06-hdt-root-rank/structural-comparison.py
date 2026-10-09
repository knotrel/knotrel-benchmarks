"""Compare parent-walk counts; no timing is measured by these probes."""
import json
from pathlib import Path
H=Path(__file__).resolve().parent
b=json.loads((H.parent/'2026-10-06-hdt-root-rank-before-probe/results.json').read_text())
a=json.loads((H.parent/'2026-10-06-hdt-root-rank-after-probe/results.json').read_text())
rows=[]
for before,after in zip(b['results'],a['results'],strict=True):
 assert all(before[k]==after[k] for k in ('nodes','workload','query_percent','trace_fingerprint_fnv1a64','trace_sha256','promotions_by_source_level'))
 changes={}
 for scope,values in before['counts'].items():
  av=after['counts'][scope]
  for metric in ('pull','join','split','ensure_calls','new_vertex_records'):assert values[metric]==av[metric],(scope,metric)
  bs=sum(values[k] for k in ('root_steps','rank_steps','fused_steps'));ats=sum(av[k] for k in ('root_steps','rank_steps','fused_steps'))
  changes[scope]={'before':values,'after':av,'parent_steps_before':bs,'parent_steps_after':ats,'parent_step_delta_percent':None if bs==0 else 100*(ats/bs-1)}
 rows.append({k:before[k] for k in ('nodes','workload','query_percent')}|{'scopes':changes})
(H/'structural-comparison.json').write_text(json.dumps({'scope':'Two identical replays per variant per trace. Identical forest restructuring/materialization counters and promotions by level. Count changes are not timing shares.','rows':rows},indent=2)+'\n')
for r in rows:print(r['nodes'],r['scopes']['promote_tree'])
